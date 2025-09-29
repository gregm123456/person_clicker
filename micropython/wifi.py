"""WiFi helper for Pico (MicroPython)

Canonical single-definition WifiManager. Ensures __init__ accepts the
optional second argument so callers that pass only wifi_cfg won't hit
the TypeError you observed.
"""
import time
try:
	import network
except Exception:
	network = None


class WifiManager:
	def __init__(self, wifi_cfg=None, cfg=None):
		# wifi_cfg expected: {"ssid": "name", "password": "pw"}
		self.wifi_cfg = wifi_cfg or {}
		self.cfg = cfg or {}
		self._wlan = None
		self._state = 'idle'
		self._last_attempt = 0
		self._attempt = 0

	def _ensure_iface(self):
		if network is None:
			return None
		if self._wlan is None:
			try:
				self._wlan = network.WLAN(network.STA_IF)
			except Exception:
				try:
					self._wlan = network.WLAN()
				except Exception:
					self._wlan = None
		return self._wlan

	def connect(self, blocking=False):
		"""Start connection.

		If blocking=True the function will attempt to connect and return
		True/False. If blocking=False it will start/advance a state machine
		and return immediately. Callers should poll is_connected() to see
		connection status.
		"""
		wlan = self._ensure_iface()
		ssid = (self.wifi_cfg or {}).get('ssid')
		password = (self.wifi_cfg or {}).get('password')

		if wlan is None:
			# no network support available on this platform
			self._state = 'no_network'
			return False

		if not ssid:
			self._state = 'no_config'
			return False

		if blocking:
			# simple blocking connect with limited retries
			wlan.active(True)
			for _ in range(6):
				try:
					wlan.connect(ssid, password)
				except Exception:
					try:
						wlan.connect((ssid, password))
					except Exception:
						pass
				t0 = time.ticks_ms()
				while time.ticks_diff(time.ticks_ms(), t0) < 5000:
					try:
						if wlan.isconnected():
							self._state = 'connected'
							return True
					except Exception:
						pass
					time.sleep(0.5)
			self._state = 'failed'
			return False

		# non-blocking: start/advance state
		self._state = 'connecting'
		self._last_attempt = time.ticks_ms() # USE TICKS_MS
		self._attempt = 0
		try:
				wlan.active(True)
				wlan.connect(ssid, password)
		except Exception:
				try:
					wlan.connect((ssid, password))
				except Exception:
					self._state = 'failed'
		return True

	def poll(self):
			"""Call regularly from the main loop to advance non-blocking connect."""
			wlan = self._ensure_iface()
			if wlan is None:
					return

			# If already connected, nothing to do.
			if self._state == 'connected':
					return

			# Check real status first. If it's connected, update state and we're done.
			try:
					if wlan.isconnected():
							print("WifiManager.poll(): isconnected() is true, updating state.")
							self._state = 'connected'
							return
			except Exception as e:
					print(f"WifiManager.poll(): isconnected() check failed: {e}")


			# If we are still trying to connect, check backoff timer to retry
			now = time.ticks_ms()
			backoff_seconds = min(60, (2 ** self._attempt))
			if time.ticks_diff(now, self._last_attempt) >= (backoff_seconds * 1000):
					print(f"WifiManager.poll(): Backoff timer expired, retrying connect (attempt {self._attempt})...")
					try:
							ssid = (self.wifi_cfg or {}).get('ssid')
							password = (self.wifi_cfg or {}).get('password')
							wlan.connect(ssid, password)
					except Exception as e:
							print(f"WifiManager.poll(): connect call failed: {e}")
					self._attempt += 1
					self._last_attempt = now

	def is_connected(self):
			wlan = self._ensure_iface()
			if wlan is None:
					return False
			try:
					# Always return the real-time status from the interface
					return wlan.isconnected()
			except Exception:
					return False

	def status(self):
			# To ensure status is always fresh, check the real interface status.
			# This prevents the app from seeing a stale 'connecting' state.
			if self.is_connected():
					self._state = 'connected'
			return self._state
