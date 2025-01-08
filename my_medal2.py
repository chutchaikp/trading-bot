
from os import path

"""hello"""
class MyMedal2:
				
	def __init__(self, country = "Thailand", gold = 0, silver = 0, bronze = 0):		
		self.country = country
		self.gold = gold
		self.bronze = bronze

	def total(self):
		return "country: {} gold: {}".format(self.country, self.gold)