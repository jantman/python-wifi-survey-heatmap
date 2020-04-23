dic = {}

try:
	dic["hallo"] = dic["tuess"]
except KeyError as kerr:
	if kerr.args[0] == 'tuess':
		print("yo")
	else:
		raise kerr
