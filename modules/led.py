from utilities import messagetypes
import requests

client = interpreter = None

def command_led_set(arg, argc):
	if 0 < argc < 3:
		if not client["led_server"]: return messagetypes.Reply("No LED server set (with 'cfg led_server')")

		color = arg[0]
		if argc > 1: value = arg[1]
		else: value = '-'

		try:
			res = requests.post(client["led_server"], data={"pos":value, "color":color}).json()
			if res["status"] == "ok": return messagetypes.Reply(res.get("message", "LEDs updated"))
			else: return messagetypes.Reply(res.get("message", "Error updating LEDs"))
		except Exception as e: return messagetypes.Reply("Something went wrong: {}".format(e))

commands = {
	"led": command_led_set
}