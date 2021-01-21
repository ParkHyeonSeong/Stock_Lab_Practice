import unittest
import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from stocklab.agent.ebest import EBest
import inspect
import time


class TestEBest(unittest.TestCase):
	def setUp(self):
		self.ebest = EBest("DEMO")
		self.ebest.login()

	def test_get_code_list(self):

		print("테스트케이스 1. ", inspect.stack()[0][3])
		# 코스피 리스트
		all_result = self.ebest.get_code_list("KOSPI")
		assert all_result is not None, '정보를 가져오지 못했습니다.'	# 가정설명문
		print("KOSPI 종목 개수 : ", len(all_result))
		# 코스닥 리스트
		all_result = self.ebest.get_code_list("KOSDAQ")
		assert all_result is not None, '정보를 가져오지 못했습니다.'
		print("KOSDAQ 종목 개수 : ", len(all_result))

	def test_get_stock_price_list_by_code(self):
		print("테스트 케이스 2. ", inspect.stack()[0][3])
		result = self.ebest.get_stock_price_by_code("005930", "2")
		assert result is not None, '정보를 가져오지 못했습니다.'
		print(result)


	def tearDown(self):
		self.ebest.logout()

if __name__ == '__main__':
    unittest.main()	# 테스트파일이 자동으로 시작되기 위한 코드