#import usocket as socket
import socket as so
import ujson
import network
from pymongo import MongoClient
import requests
import json
import string
from sklearn import model_selection
from sklearn import svm
from sklearn.linear_model import LogisticRegression
import pickle
import numpy as np
client = MongoClient()
# select test as the database
db = client.test

addr = so.getaddrinfo('0.0.0.0', 3001)[0][-1]
s = so.socket()
s.bind(addr)
s.listen(1)
print('listening')
#recv_buf = b''

#status = 0

while True:
	cl, addr = s.accept()
	print cl
	result0 = cl.recv(8192)
	result = result0.encode('utf-8')
	print('result0 =' + result0)
	print('result = ' + result)
	print('length = ', len(result))


	print('client connected from', addr)
	result_split = result.split('\r\n\r\n')
	print('result_split =', result_split)
	result_json_str = result_split[1]
	print('result_json_str =', result_json_str)
	#phase json
	result_json = json.loads(result_json_str)
	resultx = result_json["x"]
	resulty = result_json["y"]
	resultz = result_json["z"]
	LABEL = ' '

	if LABEL != ' ':
		train = db.train_data.insert_one(
			{
			'x': resultx,
			'y': resulty,
			'z': resultz,
			'label': LABEL
			})
	else: 
		predict = db.predeict_data.insert_one(
			{
			'x': resultx,
			'y': resulty,
			'z': resultz,
			'label': LABEL
			})

		width, height = 60, 1
		Matrix_predict = [[0 for x in range(width)] for y in range(height)]
		cur_predict = db.predeict_data.find_one()

		i = 0
		for i in range(20):
			Matrix_predict[0][i] = cur_predict['x'][i]
			Matrix_predict[0][i+20] = cur_predict['y'][i]
			Matrix_predict[0][i+40] = cur_predict['z'][i]
		i = 0

		db.predeict_data.remove({})
		X_predict = np.array(Matrix_predict)
		print(X_predict)

		filename = 'finalized_model.sav'
		#data test
		# load the model from disk and do predocting
		loaded_model = pickle.load(open(filename, 'rb'))
		response_predict = loaded_model.predict(X_predict)
		print(response_predict)
		print(type(response_predict))
		n = np.array2string(response_predict)
		n = '{' + n[2:3] + '}'
		print n


	#cl.send("HTTP/1.1 200 Ok\r\nContent-Type: application/text\r\nContext-Length: 10\r\n\r\n(response_predict)")
	HTTP_HEADER = 'HTTP/1.1 ' + '200' + '\r\n'
	# build a response(the response from the ml model)
	response = HTTP_HEADER + 'Content-Length:' + str(len(response_predict)) + '\r\nContent-Type: application/x-www-form-urlencoded\r\n\r\n' + 'command=show%20gesture&string=' + n
	# send response and close socket
	print(cl.send(response))
	cl.close
	print response


	