import configparser
import win32com.client
import pythoncom
from datetime import datetime			# Transaction 생성 제한
import time

class XASession:
	# 로그인 상태를 확인하기 위한 클래스 변수
	login_state = 0

	def OnLogin(self, code, msg):
		# 로그인 시도 후 호출되는 이벤트
		# code가 0000이면 로그인 성공
		if code == "0000":	# 성공
			print("입력된 계정으로 로그인에 성공하였습니다.")
			XASession.login_state = 1
		else:
			print(code, msg)
	
	def OnDisconnect(self):
		# 서버와 연결이 끊어지면 발생하는 이벤트
		print("주식거래프로그램을 종료합니다.")
		XASession.login_state = 0

class XAQuery:
	RES_PATH = "C:\\eBEST\\xingAPI\\Res\\"
	tr_run_state = 0

	def OnReceiveData(self, code):
		print("OnReceiveData", code)
		XAQuery.tr_run_state = 1

	def OnReceiveMessage(self, error, code, message):
		print("OnReceiveMessage", error, code, message)

class EBest:
	QUERY_LIMIT_10MIN = 200	# 10분당 200개의 트랜젝션 제한
	LIMIT_SECONDS = 600		# 10분

	def __init__(self, mode=None):
		# config.ini 파일을 로드하여 사용자, 서버 정보를 저장
		# query_cnt는 10분당 200개의 Transaction수행을 관리하기 위한 리스트
		# xa_session_client는 XASession 객체
		# :param mode:str - 모의서버는 DEMO 실서버는 PROD로 구분

		if mode not in ["PROD", "DEMO"]:
			raise Exception("Need to run_mode(PROD or DEMO)")

		run_mode = "EBEST_" + mode							# 모드결정
		config = configparser.ConfigParser()				# 파서 불러오기
		config.read('T:\DEV\Stock_Lab\conf\config.ini')		# 해당 파일의 내용을 읽어옴
		self.user = config[run_mode]['user']				# run_mode의 내용을 중심으로 user의 정보를 불러옴
		self.passwd = config[run_mode]['password']
		self.cert_passwd = config[run_mode]['cert_passwd']
		self.host = config[run_mode]['host']
		self.port = config[run_mode]['port']
		self.account = config[run_mode]['account']

		self.xa_session_client = win32com.client.DispatchWithEvents("XA_Session.XASession",XASession)
		self.query_cnt = []

	def login(self):
		self.xa_session_client.ConnectServer(self.host, self.port) # 서버연결 시도
		self.xa_session_client.Login(self.user, self.passwd, self.cert_passwd, 0, 0) # 인증
		while XASession.login_state == 0:
			pythoncom.PumpWaitingMessages()	# 오류메시지를 기다림

	def logout(self):
		# result = self.xa_session_client.Logout()
		# if result :
		XASession.login_state = 0	# 변수 확인
		self.xa_session_client.DisconnectServer()	# 서버종료
		print("프로그램이 정상적으로 로그아웃되었습니다.")

	def _excute_query(self, res, in_block_name, out_block_name, *out_fields, **set_fields):
		"""
		Transaction 코드를 실행하기위한 메서드
		:param res:str 리소스이름(TR)
		:param in_block_name:str 인블럭 이름
		:param out_block_name:str 아웃블럭 이름
		:param out_params:list 출력 필드 리스트
		:param in_params:dict 인블럭에 설정할 필드 딕셔너리
		:return result:list 결과를 list에 담아 리턴
		"""
		time.sleep(1)
		print("Current Query Count : ", len(self.query_cnt))
		print(res, in_block_name, out_block_name)
		while len(self.query_cnt) >= EBest.QUERY_LIMIT_10MIN:	# 전송횟수 초과시 1초 대기
			time.sleep(1)
			print("Wating for excute query...\nCurrent query count : ", len(self.query_cnt_))
			self.query_cnt = list(filter(lambda x: (datetime.today() - x).total_seconds() < EBest.LIMIT_SECONS, self.query_cnt))
		
		xa_query = win32com.client.DispatchWithEvents("XA_DataSet.XAQuery", XAQuery)
		print("테스트 : ", XAQuery.RES_PATH + res + ".res")
		xa_query.LoadFromResFile(XAQuery.RES_PATH + res + ".res")

		# in_block_name Setting
		for key, value in set_fields.items():
			xa_query.SetFieldData(in_block_name, key, 0, value)
		errorCode = xa_query.Request(0)

		# 요청 후 대기
		waiting_cnt = 0
		while xa_query.tr_run_state == 0:
			waiting_cnt +=1
			if waiting_cnt % 100000 == 0:
				print("Waiting...", self.xa_session_client.GetLastError())
			pythoncom.PumpWaitingMessages()

		# 결과 블럭
		result = []
		count = xa_query.GetBlockCount(out_block_name)
		for i in range(count):
			item = {}
			for field in out_fields:
				value = xa_query.GetFieldData(out_block_name, field, i)
				item[field] = value
			result.append(item)

		# 제약시간 체크
		XAQuery.tr_run_state = 0
		self.query_cnt.append(datetime.today())

		# 영문 필드명을 한글 필드명으로 보기 쉽게 변환
		for item in result:
			for field in list(item.keys()):
				if getattr(field, res, None):
					res_field = getattr(field, res, None)
					if out_block_name in res_field:
						field_hname = res_field[out_block_name]
						if field in field_hname:
							item[field_hname[field]] = item[field]
							item.pop(field)

		return result

	def get_code_list(self, market=None):

		"""
		TR : t8436 코스피, 코스닥의 종목 리스트 가져오기
		:param market:str 전체(0) 코스피(1) 코스닥(2)	
		:return result:list 시장별 종목리스트
		"""

		if market != "ALL" and market != "KOSPI" and market != "KOSDAQ":
			raise Exception("Need to market param(ALL, KOSPI, KOSDAQ)")

		market_code = {"ALL":"0", "KOSPI":"1", "KOSDAQ":"2"}
		print(market_code[market])
		in_params = {"gubun":market_code[market]}
		out_params = ['hname', 'shcode', 'excode', 'etfgubun', 'memedan', 'gubun', 'spac_gubun']
		result = self._excute_query("t8436", "t8436InBlock", "t8436OutBlock", *out_params, **in_params)
		return result