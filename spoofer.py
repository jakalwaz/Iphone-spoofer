"""
spoofer.py — pymobiledevice3 wrapper for iOS GPS spoofing.

iOS 17+ / iOS 26: CoreDeviceTunnelProxy (direct USB, requires admin).
Older iOS: DtSimulateLocation via lockdown (fallback).
"""

import asyncio
import queue as Q
import threading
import logging

logger = logging.getLogger(__name__)

# Lockdown path — older iOS
try:
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.simulate_location import DtSimulateLocation
    from pymobiledevice3.services.mobile_image_mounter import auto_mount
    from pymobiledevice3.exceptions import AlreadyMountedError
    LOCKDOWN_AVAILABLE = True
except ImportError:
    LOCKDOWN_AVAILABLE = False

# Tunnel path — iOS 17+ / iOS 26
try:
    from pymobiledevice3.remote.tunnel_service import CoreDeviceTunnelProxy
    from pymobiledevice3.remote.remote_service_discovery import RemoteServiceDiscoveryService
    from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
    from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
    TUNNEL_AVAILABLE = True
except ImportError:
    TUNNEL_AVAILABLE = False


async def _mount_ddi(ld):
    """Mount the Developer Disk Image; location simulation needs it. No-op if already mounted."""
    try:
        await auto_mount(ld)
    except AlreadyMountedError:
        pass
    except Exception as e:
        logger.warning(f"DDI auto-mount: {e}")


class DeviceSpoofer:
    def __init__(self):
        self._lock = threading.Lock()
        self._connected = False
        self._device_name = None
        self._ios_version = None
        self._current_lat = None
        self._current_lon = None

        # Lockdown path
        self._lockdown = None
        self._location_service = None
        self._lockdown_loop = None      # persistent event loop for lockdown async calls

        # Tunnel path
        self._rsd = None
        self._dvt = None
        self._ls = None
        self._tunnel_thread = None
        self._tunnel_stop = None
        self._tunnel_loop = None        # tunnel thread's event loop

    # ------------------------------------------------------------------
    # Helpers — run async code on the correct event loop
    # ------------------------------------------------------------------

    def _lockdown_run(self, coro):
        """Run a coroutine on the persistent lockdown event loop."""
        return self._lockdown_loop.run_until_complete(coro)

    def _tunnel_run(self, coro):
        """Schedule a coroutine on the tunnel thread's event loop and wait for result."""
        fut = asyncio.run_coroutine_threadsafe(coro, self._tunnel_loop)
        return fut.result(timeout=10)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def connect(self):
        with self._lock:
            if self._connected:
                return

            # 1. Try lockdown (works for older iOS)
            if LOCKDOWN_AVAILABLE:
                try:
                    self._connect_lockdown()
                    self._connected = True
                    logger.info("Connected via lockdown")
                    return
                except Exception as e:
                    logger.info(f"Lockdown failed ({e}), trying CoreDevice tunnel…")

            # 2. CoreDevice tunnel (iOS 17+ / iOS 26)
            if TUNNEL_AVAILABLE:
                try:
                    self._connect_tunnel()
                    self._connected = True
                    logger.info("Connected via CoreDevice tunnel")
                    return
                except Exception as e:
                    logger.error(f"Tunnel failed: {e}")
                    raise RuntimeError(str(e))

            raise RuntimeError(
                "pymobiledevice3 is not installed. Run: pip install pymobiledevice3"
            )

    def set_location(self, lat: float, lon: float):
        with self._lock:
            if not self._connected:
                raise RuntimeError("Not connected")
            try:
                if self._ls is not None:
                    self._tunnel_run(self._ls.set(lat, lon))
                elif self._location_service is not None:
                    self._lockdown_run(self._location_service.set(lat, lon))
                self._current_lat = lat
                self._current_lon = lon
            except Exception as e:
                self._connected = False
                raise RuntimeError(f"Failed to set location: {e}")

    def stop_simulation(self):
        with self._lock:
            if not self._connected:
                return
            try:
                if self._ls is not None:
                    self._tunnel_run(self._ls.clear())
                elif self._location_service is not None:
                    self._lockdown_run(self._location_service.clear())
                self._current_lat = None
                self._current_lon = None
            except Exception as e:
                logger.warning(f"stop_simulation error: {e}")

    def disconnect(self):
        with self._lock:
            self._connected = False
            self._current_lat = None
            self._current_lon = None

            # Clear simulation on tunnel loop BEFORE signaling stop
            if self._ls is not None and self._tunnel_loop is not None:
                try:
                    self._tunnel_run(self._ls.clear())
                except Exception:
                    pass
                self._ls = None

            # Signal the background tunnel thread to exit
            if self._tunnel_stop is not None:
                self._tunnel_stop.set()
                self._tunnel_stop = None

            if self._tunnel_thread is not None:
                self._tunnel_thread.join(timeout=5)
                self._tunnel_thread = None

            self._tunnel_loop = None

            if self._dvt is not None:
                try:
                    self._dvt.close()
                except Exception:
                    pass
                self._dvt = None

            if self._rsd is not None:
                self._rsd = None

            # Lockdown path cleanup
            if self._location_service is not None:
                try:
                    if self._lockdown_loop is not None:
                        self._lockdown_run(self._location_service.clear())
                except Exception:
                    pass
                try:
                    self._location_service.close()
                except Exception:
                    pass
                self._location_service = None

            if self._lockdown_loop is not None:
                try:
                    self._lockdown_loop.close()
                except Exception:
                    pass
                self._lockdown_loop = None

            self._device_name = None
            self._ios_version = None

    def get_status(self) -> dict:
        return {
            "connected": self._connected,
            "device": self._device_name,
            "ios": self._ios_version,
            "lat": self._current_lat,
            "lon": self._current_lon,
        }

    # ------------------------------------------------------------------
    # Private — lockdown path (older iOS)
    # ------------------------------------------------------------------

    def _connect_lockdown(self):
        loop = asyncio.new_event_loop()
        self._lockdown_loop = loop

        ld = loop.run_until_complete(create_using_usbmux())
        self._device_name = ld.display_name or ld.udid[:8]
        self._ios_version = ld.product_version
        if int(ld.product_version.split(".")[0]) >= 17:
            raise RuntimeError("iOS 17+ needs the CoreDevice tunnel")
        loop.run_until_complete(_mount_ddi(ld))

        svc = DtSimulateLocation(lockdown=ld)
        loop.run_until_complete(svc.set(0.0, 0.0))
        loop.run_until_complete(svc.clear())

        self._lockdown = ld
        self._location_service = svc

    # ------------------------------------------------------------------
    # Private — CoreDevice tunnel path (iOS 17+ / iOS 26)
    # ------------------------------------------------------------------

    def _connect_tunnel(self):
        """
        Establish a CoreDevice tunnel directly over USB using CoreDeviceTunnelProxy.
        Runs the async tunnel in a daemon background thread.
        """
        result_q = Q.Queue()
        stop_event = threading.Event()
        self._tunnel_stop = stop_event

        async def _run_tunnel():
            ld = await create_using_usbmux()
            proxy = await CoreDeviceTunnelProxy.create(ld)
            async with proxy.start_tcp_tunnel() as tunnel_result:
                try:
                    logger.info(f"Tunnel up: {tunnel_result.address}:{tunnel_result.port}")
                    async with RemoteServiceDiscoveryService(
                        (tunnel_result.address, tunnel_result.port)
                    ) as rsd:
                        logger.info(f"RSD: {rsd.product_type} {rsd.product_version}")
                        await _mount_ddi(rsd)
                        async with DvtProvider(rsd) as dvt, LocationSimulation(dvt) as ls:
                            result_q.put(("ok", rsd, ls, ld.display_name))
                            # Keep the tunnel alive until disconnect() signals us
                            await asyncio.get_running_loop().run_in_executor(None, stop_event.wait)
                except Exception as exc:
                    import traceback
                    logger.error(f"Setup failed:\n{traceback.format_exc()}")
                    if result_q.empty():
                        result_q.put(("error", exc))

        def _thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._tunnel_loop = loop
            try:
                loop.run_until_complete(_run_tunnel())
            except Exception as exc:
                import traceback
                logger.error(f"Tunnel thread exception:\n{traceback.format_exc()}")
                if result_q.empty():
                    result_q.put(("error", exc))
            finally:
                loop.close()

        t = threading.Thread(target=_thread, daemon=True, name="TunnelThread")
        t.start()
        self._tunnel_thread = t

        # Wait up to 30 s for the tunnel to come up
        try:
            item = result_q.get(timeout=30)
        except Q.Empty:
            stop_event.set()
            raise RuntimeError(
                "CoreDevice tunnel timed out (30 s).\n\n"
                "Make sure:\n"
                "  1. Developer Mode is ON  (Settings → Privacy & Security → Developer Mode)\n"
                "  2. iPhone is unlocked and plugged in\n"
                "  3. This app is running as Administrator\n"
            )

        if item[0] == "error":
            raise item[1]

        _, rsd, ls, name = item
        self._rsd = rsd
        self._ls = ls

        self._device_name = name or rsd.product_type
        self._ios_version = rsd.product_version
