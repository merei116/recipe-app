from django.test import SimpleTestCase

from app import calc

class CalcTests(SimpleTestCase):
    def test_add(self):
        res = calc.add(5, 6)
        self.assertEqual(res, 11)
    
    def test_subctract(self):
        res = calc.substract(10, 15)
        self.assertEqual(res, 5)
        