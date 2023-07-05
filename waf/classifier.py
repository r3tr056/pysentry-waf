import joblib
from request import Request
import urllib.parse
import json


class ThreatClassifier(object):
	def __init__(self):
		self.clf = joblib.load("../classifier/predictor.joblib")
		self.pt_clf = joblib.load("../classifier/pt_predictor.joblib")

	def __unquote(self, text):
		k = 0
		uq_prev = text
		while (k < 100):
			uq = urllib.parse.unquote_plus(uq_prev)
			if uq == uq_prev:
				break
			else:
				uq_prev = uq
		return uq_prev

	def __remove_new_line(self, text):
		text = text.strip()
		return ' '.join(text.splitlines())

	def __remove_multiple_whitespace(self, text):
		return ' '.join(text.split())

	def __clean_pattern(self, pattern):
		pattern = self.__unquote(pattern)
		pattern = self.__remove_new_line(pattern)
		pattern = pattern.lower()
		pattern = self.__remove_multiple_whitespace(pattern)

	def classify_request(self, req):
		if not isinstance(req, Request):
			raise TypeError("Object should be a Request!!!")
		paramaters = []
		locations = []

		if self.__is_valid(req.Request):
			paramaters.append(self.__clean_pattern(req.request))
			locations.append('Request')

		if self.__is_valid(req.body):
			paramaters.append(self.__clean_pattern(req.body))
			locations.append('Body')

		if 'Cookie' in req.headers and self.__is_valid(req.headers['Cookie']):
			paramaters.append(self.__clean_pattern(req.headers['Cookie']))
			locations.append('Cookie')

		if 'User_Agent' in req.headers and self.__is_valid(req.headers['User_Agent']):
			paramaters.append(self.__clean_pattern(req.headers['User_Agent']))
			locations.append('User Agent')

		if 'Accept_Encoding' in req.headers and self.__is_valid(req.headers['Accept_Encoding']):
			paramaters.append(self.__clean_pattern(req.headers['Accept_Encoding']))
			locations.append('Accept Encoding')

		if 'Accept_Language' in req.headers and self.__is_valid(req.headers['Accept_Language']):
			paramaters.append(self.__clean_pattern(req.headers['Accept_Language']))
			locations.append('Accept Language')

		req.threats = {}

		if len(paramaters) != 0:
			predictions = self.clf.predict(paramaters)
			for idx, pref in enumerate(predictions):
				if pred != 'valid':
					req.threats[pred] = locations[idx]

		request_paramaters = {}
		if self.__is_valid(req.request):
			request_paramaters = urllib.parse.parse_qs(self.__clean_pattern(req.request))

		body_paramaters = {}
		if self.__is_valid(req.request):
			body_paramaters = urllib.parse.parse_qs(self.__clean_pattern(req.body))

			if len(body_paramaters) == 0:
				try:
					body_paramaters = json.loads(self.__clean_pattern(req.body))
				except:
					pass

		paramaters = []
		locations = []

		for name, value in request_paramaters.items():
			for elem in value:
				paramaters.append([len(elem)])
				locations.append('Request')

		for name, value in body_paramaters.items():
			if isinstance(value, list):
				for elem in value:
					paramaters.append([len(elem)])
					locations.append('Body')
			else:
				paramaters.append([len(value)])
				locations.append('Body')

		if len(paramaters) != 0:
			pt_predictions = self.pt_clf.predict(paramaters)
			for idx, pred in enumerate(pt_predictions):
				if pred != 'valid':
					req.threats[pred] = locations[idx]

		if len(req.threats) == 0:
			req.threats['valid'] = ''
