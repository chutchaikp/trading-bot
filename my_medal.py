class MyMedal:
	
	def __init__(self, country = "Thailand", gold = 0, silver = 0, bronze = 0):
		self.country = country
		self.gold = gold
		self.silver = silver
		self.bronze = bronze

	# def total(self):
	# 	# format string len
	# 	return "country: {:15} g: {:3} s: {:3} b: {:3} ".format(self.country, self.gold, self.silver, self.bronze)
	
	def __str__(self):		
		print('xx')
		return "hello"
		# // return "country: {:15} g: {:3} s: {:3} b: {:3} ".format(self.country, self.gold, self.silver, self.bronze)
	
