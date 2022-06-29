from metaflow import FlowSpec, step


class WorldFlow(FlowSpec):
	@step
	def start(self):
		print("starting")
		self.next(self.end)

	@step
	def end(self):
		print("ending")

if __name__ == '__main__':
	WorldFlow()