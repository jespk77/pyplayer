import os

def hello_world():
	print("hello world")
	if "key" in os.environ: print(os.environ["key"])

if __name__ == "__main__":
	hello_world()