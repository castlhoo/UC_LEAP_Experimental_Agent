from __future__ import division
import sys
import numpy as np
from scipy import optimize
from scipy import stats
import scipy
import math
import labrad
from lanczos import deriv
from numpy.linalg import inv
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
from mpl_toolkits.mplot3d.axes3d import get_test_data

class TuningForkError():

	'''
	self.ACdata
	self.Xdata
	self.Ydata
	self.dvPath
	self.originalData
	self.ProcessedData
	'''

	def init_tf_fitting(self, dvNum, Trace = 0, inGain = 1000):
		'''
		This function initializes the Tuning Fork Fitting Program:
		init_tf_fitting(dvNum, Trace = 0, inGain = 1000)

		dvNum (str): Name of the data vault file
		Trace (int): {Trace = 0|Retrace = 1}
		inGain (float): Gain of the DC measurement		
		'''
		self.FitFlag = False
		self.dvPath = dvNum
		self.TraceFlag = Trace
		self.gain = inGain

		try:
			cxn = labrad.connect()
			dv = cxn.data_vault()
			dv.open(self.dvPath)
			self.originalData = dv.get()

		except Exception as inst:
			print 'Error opening Data Vault: ', inst
			print 'Error thrown on line: ', sys.exc_traceback.tb_lineno

		self.ProcessedData = self.ProcessRawData(self.originalData)
		#self.RotateACData() 
		self.OriginalACdata = self.SetupPlotData(7)
		self.DCdata = self.SetupPlotData(5)
		self.ACXQuad = self.SetupPlotData(6)
		self.ACXQuad = self.ACXQuad - self.ACXQuad[0,0]
		self.ACYQuad = self.SetupPlotData(7)
		self.ACYQuad = self.ACYQuad - self.ACYQuad[0,0]
		#self.CropData1(40)
		self.RotateACData()
		self.Xdata = self.xDeriv()
		self.Ydata = self.yDeriv()
		#self.CropData(40)
		#self.Xdata = np.gradient(self.DCdata, self.xscale, axis = 0)
		#self.Ydata = np.gradient(self.DCdata, self.yscale, axis = 1)
		# self.Xdata = np.gradient(self.DCdata, self.xscale, axis = 0)
		# self.Ydata = np.gradient(self.DCdata, self.yscale, axis = 1)
		self.CropData(5)
		#self.XPdata = np.gradient(self.DCdata, self.xscale, axis = 0)
		#self.YPdata = np.gradient(self.DCdata, self.yscale, axis = 1)

		try:
			self.DataCheck()
		except Exception as inst:
			print 'Error Checking Data: ', inst
			print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
			
#----------------------------------------------------------------This Part Processes Data-------------------------------------------------------------------#
	def DataCheck(self):
		if self.ACdata.shape == self.Xdata.shape and self.Xdata.shape == self.Ydata.shape:
			self.FitFlag = True
			return 'Initialization Successful'
		else:
			self.FitFlag = False
			return 'Failed to Initialize: Wrong Data Set'


	def ProcessRawData(self, rawData):
		try:
			#self.indVars=self.indVars[1::]
			#self.NumberofindexVariables -=1
			self.traceData, self.retraceData = self.split(rawData, rawData[:,0] == 0)
			self.traceData = np.delete(self.traceData,0,1)
			self.retraceData = np.delete(self.retraceData,0,1)
			if self.TraceFlag == 0:
				ProcessedData = self.traceData
			elif self.TraceFlag == 1:
				ProcessedData = self.retraceData
			return ProcessedData

		except Exception as inst:
			print 'Error processing raw data: ', inst
			print 'Error thrown on line: ', sys.exc_traceback.tb_lineno


	def SetupPlotData(self, zIndex):
		# set parameters
		try:
			self.xMax = np.amax(self.ProcessedData[::,0])
			self.xMin = np.amin(self.ProcessedData[::,0])
			#self.deltaX = self.xMax - self.xMin
			self.xPoints = np.amax(self.ProcessedData[::,0])+1  #look up the index
			self.xscale = ((np.amax(self.ProcessedData[::,2]) - np.amin(self.ProcessedData[::,2])) / (self.xPoints - 1)) * 5.36
			self.yMax = np.amax(self.ProcessedData[::,1])
			self.yMin = np.amin(self.ProcessedData[::,1])
			#yMax = self.PlotParameters['yMax'] * self.parent.SettingWindow.Setting_Parameter['ScaleFactor']
			#self.PlotParameters['yMin'] = self.PlotParameters['yMin'] * self.parent.SettingWindow.Setting_Parameter['ScaleFactor']
			#self.deltaY = self.yMax - self.yMin
			self.yPoints = np.amax(self.ProcessedData[::,1])+1
			self.yscale = ((np.amax(self.ProcessedData[::,3]) - np.amin(self.ProcessedData[::,3])) / (self.yPoints - 1)) * 5.36
		except Exception as inst:
			print 'Following error was thrown: ', inst
			print 'Error thrown on line: ', sys.exc_traceback.tb_lineno


		try:
			Data = np.zeros([int(self.xPoints), int(self.yPoints)])
			for i in self.ProcessedData:
				Data[int(i[0]), int(i[1])] = i[zIndex]
			return Data
		except Exception as inst:
			print 'Following error was thrown: ', inst
			print 'Error thrown on line: ', sys.exc_traceback.tb_lineno

	#Fitting a phase angle for x and y quadrature
	def RotateACData(self):
		self.arctan = np.arctan2(self.ACYQuad, self.ACXQuad)
		self.flatArctan = self.arctan.flatten()
		self.ThetaFit()
		self.ACdata = np.sqrt(np.square(self.ACXQuad) + np.square(self.ACYQuad))*(np.cos(self.arctan - self.thetafit))
		self.ACROTATE = np.sqrt(np.square(self.ACXQuad) + np.square(self.ACYQuad))*(np.cos(self.arctan - self.thetafit))
		self.ACRES = np.sqrt(np.square(self.ACXQuad) + np.square(self.ACYQuad))*(np.sin(self.arctan - self.thetafit))
		#self.phasePlot = np.cos(self.arctan - self.thetafit)
		self.phasePlot = np.degrees(self.arctan - self.thetafit)
		#self.phaseBefore = (180 / np.pi)  * self.arctan
		ErrorSquare = np.sum(np.square(np.sqrt(np.square(self.FlatACXQuad) + np.square(self.FlatACYQuad))*(np.sin(self.flatArctan - self.thetafit))))
		Sigma = np.sqrt(ErrorSquare) / len(self.flatArctan)

		
		print('Rotation Error Sigma is: ' + str(Sigma))

	def ThetaFunction(self, para):
		return np.sum(np.square(np.sqrt(np.square(self.FlatACXQuad) + np.square(self.FlatACYQuad))*(np.sin(self.flatArctan - para))))

	def ThetaFit(self):
		p0 = np.mean(self.arctan)
		self.FlatACXQuad = self.ACXQuad.flatten()
		self.FlatACYQuad = self.ACYQuad.flatten()
		self.FitTheta = scipy.optimize.minimize(self.ThetaFunction, p0, method = 'Nelder-Mead')
		Success = self.FitTheta.success
		if Success:
			self.thetafit = self.FitTheta.x
			#self.offset_for_phase_fitting = self.fitResult[1]
			self.theta = np.degrees(np.arctan(self.thetafit))
			print('Rotation Fit successful, Theta is ' + str(self.theta))
		elif not Success:
			print('Failure: ' + str(FitTheta.message))


	#Taking X and Y derivatives of AC data
	def xDeriv(self):
		Data = np.zeros([int(self.xPoints), int(self.yPoints)])
		try:
			xVals = np.linspace(self.xMin, self.xMax, num = self.xPoints) * self.xscale
			delta = (abs(self.xMax - self.xMin) * self.xscale) / self.xPoints
			for i in range(0, self.DCdata.shape[1]):
				Data[:, i] = deriv(self.DCdata[:,i], xVals, 5, delta, 2, 5)
			#print 'ok'
			return Data
		except Exception as inst:
			print 'Error When Taking X Derivative: ', inst

	def yDeriv(self):
		Data = np.zeros([int(self.xPoints), int(self.yPoints)])
		yVals = np.linspace(self.yMin, self.yMax, num = self.yPoints) * self.yscale
		delta = (abs(self.yMax - self.yMin) * self.yscale) / self.yPoints
		for i in range(0, self.DCdata.shape[0]):
			Data[i, :] = deriv(self.DCdata[i,:], yVals, 2, delta, 1, 2)
		return Data

	def split(self, arr, cond):
		return [arr[cond], arr[~cond]]  

	def CropData(self, EdgePixels = 1):
		try:
			row = np.append(np.linspace(0, EdgePixels - 1, num = EdgePixels, dtype = np.int64), np.linspace(int(self.yPoints) - EdgePixels, int(self.yPoints) - 1, num = EdgePixels, dtype = np.int64))
			col = np.append(np.linspace(0, EdgePixels - 1, num = EdgePixels, dtype = np.int64), np.linspace(int(self.xPoints) - EdgePixels, int(self.xPoints) - 1, num = EdgePixels, dtype = np.int64)) 
			self.ACdata = np.delete(self.ACdata, row, axis = 1)
			self.ACdata = np.delete(self.ACdata, col, axis = 0)
			self.DCdata = np.delete(self.DCdata, row, axis = 1)
			self.DCdata = np.delete(self.DCdata, col, axis = 0)
			self.Xdata = np.delete(self.Xdata, row, axis = 1)
			self.Xdata = np.delete(self.Xdata, col, axis = 0)
			self.Ydata = np.delete(self.Ydata, row, axis = 1)
			self.Ydata = np.delete(self.Ydata, col, axis = 0)
		except Exception as inst:
			print 'Error when cropping data: '+ inst
			print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
	'''
	def CropData1(self, EdgePixels = 1):
		try:
			row = np.append(np.linspace(0, EdgePixels - 1, num = EdgePixels, dtype = np.int64), np.linspace(int(self.yPoints) - EdgePixels, int(self.yPoints) - 1, num = EdgePixels, dtype = np.int64))
			#col = np.append(np.linspace(0, EdgePixels - 1, num = EdgePixels, dtype = np.int64), np.linspace(int(self.xPoints) - EdgePixels, int(self.xPoints) - 1, num = EdgePixels, dtype = np.int64)) 
			col = np.append(np.linspace(0, 115 - 1, num = 115, dtype = np.int64), np.linspace(int(self.xPoints) - 115, int(self.xPoints) - 1, num = 115, dtype = np.int64))
			self.ACdata = np.delete(self.ACdata, row, axis = 1)
			self.ACdata = np.delete(self.ACdata, col, axis = 0)
			self.DCdata = np.delete(self.DCdata, row, axis = 1)
			self.DCdata = np.delete(self.DCdata, col, axis = 0)
			#self.Xdata = np.delete(self.Xdata, row, axis = 1)
			#self.Xdata = np.delete(self.Xdata, col, axis = 0)
			#self.Ydata = np.delete(self.Ydata, row, axis = 1)
			#self.Ydata = np.delete(self.Ydata, col, axis = 0)
		except Exception as inst:
			print 'Error when cropping data: '+ inst
			print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
	'''
#---------------------------------------------------------------This Part is Curve Fitting-------------------------------------------------------------------#
	'''
	def MinimizeFitTuningForkData(self):
		if self.FitFlag:
			self.Fit = scipy.optimize.minimize(self.SquareDifference_Weight, [1.0, 1.0], method = 'Nelder-Mead')
			Success = self.Fit.success
			if Success:
				self.fitparameter = self.Fit.x
				self.amplitude = math.sqrt(self.fitparameter[0] ** 2 + self.fitparameter[1] ** 2)
				self.angle = (180.0 / math.pi * math.atan2(self.fitparameter[0], self.fitparameter[1]))
				print('Fit successful, X component is ' + str(self.fitparameter[0]) + ' and Y component is ' + str(self.fitparameter[1]) + '. The amplitude is ' + str(self.amplitude) + ' and the angle is ' + str(self.angle))
				#self.ErrorPropagation()
			elif not Success:
				print('Failure: ' + str(Fit.message))
		else:
			print('Data Fitting Disabled due to error in shape of data')

	def SquareDifference_Weight(self, weight):
		gain = float(self.gain)
		DataSubtracted = self.ACdata.flatten() -  weight[0] * self.Xdata.flatten() * gain - weight[1] * self.Ydata.flatten() * gain
		Square = np.sum(np.square(DataSubtracted))
		return Square
	'''

	def FittingFunction(self, Data, *weight):
		FlatXData, FlatYData = Data
		return weight[0] * FlatXData + weight[1] * FlatYData + weight[2]

	def CurveFit(self):
		p0 = 1, 1, 0
		FlatXData = self.Xdata.flatten() * self.gain
		FlatYData = self.Ydata.flatten() * self.gain
		popt, pcov = scipy.optimize.curve_fit(self.FittingFunction, (FlatXData, FlatYData), self.ACdata.flatten(), p0)
		self.fitparameter = popt
		self.perr = np.sqrt(np.diag(pcov))
		self.amplitude = math.sqrt(self.fitparameter[0] ** 2 + self.fitparameter[1] ** 2)
		self.angle = (180.0 / math.pi * math.atan2(self.fitparameter[0], self.fitparameter[1]))
		print('Fit successful, X component is ' + str(self.fitparameter[0]) + ' and Y component is ' + str(self.fitparameter[1]) + '. The amplitude is ' + str(self.amplitude) + ' and the angle is ' + str(self.angle))
		print('Offset is' + str(self.fitparameter[2]))

#-------------------------------------------------------------This Part is Error Propagation----------------------------------------------------------------#
	'''
	def MinimizeErrorPropagation(self):
		try:
			#FitX, FitY, amplitude, angle = self.FitTuningForkData()
			FlatAC = self.ACdata.flatten()
			FlatDCX = self.Xdata.flatten() * self.gain
			FlatDCY = self.Ydata.flatten() * self.gain
			FlatDC = self.fitparameter[0] * FlatDCX + self.fitparameter[1] * FlatDCY
			l = len(FlatAC)
			Cov = np.sum(np.multiply(FlatDCX, FlatDCY))
			#chisq = scipy.stats.chisquare(FlatAC * 1000, FlatDC * 1000)
			#S = np.sqrt(chisq[0] / 1000)
			S = np.sum(np.square(FlatAC - FlatDC))
			print 'S = ', str(S), 'Sigma = ', str(S/l), 'Maxium of ACdata = ', str(np.amax(abs(self.ACdata)))
			CovMatrix = np.array([[np.sum(np.square(FlatDCX)),Cov],[Cov,np.sum(np.square(FlatDCY))]])

			try:
				InvCovMatrix = inv(CovMatrix)
			except Exception as inst:
				print inst
				print 'Error thrown on line: ', sys.exc_traceback.tb_lineno

			SigmaX = np.sqrt((S / (l - 1)) * InvCovMatrix[0][0])
			SigmaY = np.sqrt((S / (l - 1)) * InvCovMatrix[1][1])
			SigmaAmp = (1 / self.amplitude) * (np.sqrt(2) * (abs(self.fitparameter[0] * SigmaX) + abs(self.fitparameter[1] * SigmaY)))
			SigmaAngle = (180.0 / math.pi) * np.sqrt((self.fitparameter[0] ** 2) * (SigmaY ** 2) + (self.fitparameter[1] ** 2) * (SigmaX ** 2)) / (self.fitparameter[0] ** 2 + self.fitparameter[1] ** 2)
			print(('Error Propaagtion Successful, Uncertainty in X is ' + str(SigmaX) + ' and Uncertainty in Y is ' + str(SigmaY)) + '. The Uncertainty in Amplitude is ' + str(SigmaAmp) + ' and the Uncertainty in Angle is ' + str(SigmaAngle))
			return SigmaX, SigmaY, SigmaAmp, SigmaAngle

		except Exception as inst:
			print 'Faliure in Calculating Error: ', inst
			print 'Error thrown on line: ', sys.exc_traceback.tb_lineno
	'''
	def ErrorCalculation(self):
		FlatAC = self.ACdata.flatten()
		FlatDCX = self.Xdata.flatten() * self.gain
		FlatDCY = self.Ydata.flatten() * self.gain
		FlatDC = self.fitparameter[0] * FlatDCX + self.fitparameter[1] * FlatDCY
		l = len(FlatAC)
		S = np.sum(np.square(FlatAC - FlatDC))
		print 'S = ', str(S), 'Sigma = ', str(S/l), 'Maxium of ACdata = ', str(np.mean(abs(self.ACdata)))
		SigmaX = self.perr[0]
		SigmaY = self.perr[1]
		SigmaAmp = (1 / self.amplitude) * (np.sqrt(2) * (abs(self.fitparameter[0] * SigmaX) + abs(self.fitparameter[1] * SigmaY)))
		SigmaAngle = (180.0 / math.pi) * np.sqrt((self.fitparameter[0] ** 2) * (SigmaY ** 2) + (self.fitparameter[1] ** 2) * (SigmaX ** 2)) / (self.fitparameter[0] ** 2 + self.fitparameter[1] ** 2)
		print(('Error Propaagtion Successful, Uncertainty in X is ' + str(SigmaX) + ' and Uncertainty in Y is ' + str(SigmaY)) + '. The Uncertainty in Amplitude is ' + str(SigmaAmp) + ' and the Uncertainty in Angle is ' + str(SigmaAngle))
		return SigmaX, SigmaY, SigmaAmp, SigmaAngle


#--------------------------------------------------------------Here is the script------------------------------------------------------------------------#
if __name__ == "__main__":
	from TuningForkError import TuningForkError
	import matplotlib.pyplot as plt
	from matplotlib.pyplot import pcolor
	QTTF = TuningForkError()
	QTTF.init_tf_fitting('09934 - nSOT Scan Data unnamed', 0, 500) #relative gain

	QTTF.CurveFit()
	QTTF.ErrorCalculation()
	#DC = QTTF.fitparameter[0] * QTTF.Xdata * QTTF.gain + QTTF.fitparameter[1] * QTTF.Ydata * QTTF.gain
	#plt.figure(1)
	FitData = QTTF.fitparameter[0] * QTTF.Xdata * QTTF.gain + QTTF.fitparameter[1] * QTTF.Ydata * QTTF.gain + QTTF.fitparameter[2]
	
	fig, axs = plt.subplots(3, 2)
	# X = np.arange(0, 18, 1)
	# Y = np.arange(0, 18, 1)
	# X, Y = np.meshgrid(X, Y)

	# plot DC
	ax = axs[0, 0]
	c = ax.pcolor(QTTF.DCdata, cmap='RdBu') #00928
	#c = ax.pcolor(QTTF.DCdata, cmap='RdBu', vmin = 0, vmax = 0.4) #00928
	#c = ax.pcolor(QTTF.DCdata, cmap='RdBu', vmin = 0.3, vmax = 1.7) #09073
	#c = ax.pcolor(QTTF.DCdata, cmap='RdBu', vmin = 0.3, vmax = 1.7) #09074
	ax.set_title('DC data')
	#ax.set_aspect('equal')
	fig.colorbar(c, ax = ax)

	# plot X derivative
	ax = axs[0, 1]
	c = ax.pcolor(QTTF.Xdata, cmap='RdBu') #00928
	#c = ax.pcolor(QTTF.Xdata, cmap='RdBu', vmin = -0.075, vmax = 0.06) #00928
	#c = ax.pcolor(QTTF.Xdata, cmap='RdBu', vmin = -0.75, vmax = 1.5) #09073
	#c = ax.pcolor(QTTF.Xdata, cmap='RdBu', vmin = -0.75, vmax = 1.5) #09074
	ax.set_title('X derivative')
	fig.colorbar(c, ax = ax)

	# plot Y derivative
	ax = axs[1, 0]
	c = ax.pcolor(QTTF.Ydata, cmap='RdBu')
	#c = ax.pcolor(QTTF.Ydata, cmap='RdBu', vmin = -0.06, vmax = 0.037)
	#c = ax.pcolor(QTTF.Ydata, cmap='RdBu', vmin = -0.75, vmax = 1.25)
	#c = ax.pcolor(QTTF.Ydata, cmap='RdBu', vmin = -0.75, vmax = 1.25)
	ax.set_title('Y derivative')
	fig.colorbar(c, ax = ax)

	# plot AC
	ax = axs[1, 1]
	c = ax.pcolor(QTTF.ACdata, cmap='RdBu')
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -4.5, vmax = 6.5)
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -2, vmax = 6)
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -3.5, vmax = 10)
	ax.set_title('AC data')
	fig.colorbar(c, ax = ax)

	# plot Fit
	ax = axs[2, 0]
	c = ax.pcolor(FitData, cmap='RdBu')
	#c = ax.pcolor(FitData, cmap='RdBu', vmin = -5, vmax = 6.5)
	#c = ax.pcolor(FitData, cmap='RdBu', vmin = -2, vmax = 4.5)
	#c = ax.pcolor(FitData, cmap='RdBu', vmin = -3.5, vmax = 10)
	ax.set_title('After Fitting')
	fig.colorbar(c, ax = ax)

	# plot Residual
	ax = axs[2, 1]
	c = ax.pcolor(QTTF.ACdata - FitData, cmap='RdBu')
	#c = ax.pcolor(QTTF.ACdata - FitData, cmap='RdBu', vmin = -1.7, vmax = 1.6)
	#c = ax.pcolor(QTTF.ACdata - FitData, cmap='RdBu', vmin = -3.5, vmax = 5)
	#c = ax.pcolor(QTTF.ACdata - FitData, cmap='RdBu', vmin = -4.5, vmax = 6)
	ax.set_title('Residual')
	fig.colorbar(c, ax = ax)


	'''
	# plot DC
	#ax = axs[0, 0]
	#c = ax.pcolor(QTTF.DCdata, cmap='RdBu', vmin = 0, vmax = 0.4) #00928
	c = ax.plot_surface(QTTF.DCdata, cmap='RdBu', vmin = 0.3, vmax = 1.7) #09073
	#c = ax.pcolor(QTTF.DCdata, cmap='RdBu', vmin = 0.3, vmax = 1.7) #09074
	ax.set_title('DC data')
	fig.colorbar(c, ax = ax)

	# plot AC
	ax = axs[0, 1]
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -4.5, vmax = 6.5)
	c = ax.plot_surface(QTTF.ACdata, cmap='RdBu', vmin = -2, vmax = 6)
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -3.5, vmax = 10)
	ax.set_title('AC data')
	fig.colorbar(c, ax = ax)
	# plot Fit
	ax = axs[0, 2]
	#c = ax.pcolor(FitData, cmap='RdBu', vmin = -5, vmax = 6.5)
	c = ax.plot_surface(FitData, cmap='RdBu', vmin = -2, vmax = 4.5)
	#c = ax.pcolor(FitData, cmap='RdBu', vmin = -3.5, vmax = 10)
	ax.set_title('After Fitting')
	fig.colorbar(c, ax = ax)
	'''

	'''
	fig = plt.figure()

	ax = fig.add_subplot(1, 3, 1, projection='3d')
	surf = ax.plot_surface(X, Y, QTTF.DCdata, rstride=1, cstride=1, cmap='RdBu',vmin = 0.3, vmax = 1.7, linewidth=0, antialiased=False)
	ax.set_title('DC data')
	fig.colorbar(surf)

	ax = fig.add_subplot(1, 3, 2, projection='3d')
	surf = ax.plot_surface(X, Y, QTTF.ACdata, rstride=1, cstride=1, cmap='RdBu',vmin = -3.5, vmax = 10, linewidth=0, antialiased=False)
	ax.set_title('TF data')
	fig.colorbar(surf)

	ax = fig.add_subplot(1, 3, 3, projection='3d')
	surf = ax.plot_surface(X, Y, FitData, rstride=1, cstride=1, cmap='RdBu',vmin = -3.5, vmax = 10, linewidth=0, antialiased=False)
	ax.set_title('Fit data')
	fig.colorbar(surf)
	'''
	#plt.show()

	fig2, axs2 = plt.subplots(3, 2)

	ax = axs2[0, 1]
	c = ax.pcolor(QTTF.ACROTATE, cmap='RdBu')
	#c = ax.pcolor(QTTF.ACROTATE, cmap='RdBu', vmin = -4, vmax = 4)
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -2, vmax = 6)
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -3.5, vmax = 10)
	ax.set_title('AC data X after Rotation')
	fig2.colorbar(c, ax = ax)

	ax = axs2[1, 0]
	c = ax.pcolor(QTTF.ACYQuad, cmap='RdBu')
	#c = ax.pcolor(QTTF.ACYQuad, cmap='RdBu', vmin = -4, vmax = 4)
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -2, vmax = 6)
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -3.5, vmax = 10)
	ax.set_title('AC data Y Quadrature')
	fig2.colorbar(c, ax = ax)

	ax = axs2[0, 0]
	c = ax.pcolor(QTTF.ACXQuad, cmap='RdBu')
	#c = ax.pcolor(QTTF.ACXQuad, cmap='RdBu', vmin = -4, vmax = 4)
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -2, vmax = 6)
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -3.5, vmax = 10)
	ax.set_title('AC data X Quadrature')
	fig2.colorbar(c, ax = ax)

	ax = axs2[1,1]
	c = ax.pcolor(QTTF.ACRES, cmap='RdBu')
	#c = ax.pcolor(QTTF.ACRES, cmap='RdBu', vmin = -4, vmax = 4)
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -2, vmax = 6)
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -3.5, vmax = 10)
	ax.set_title('AC data Y after rotation')
	fig2.colorbar(c, ax = ax)

	ax = axs2[2,0]
	c = ax.pcolor(np.degrees(QTTF.arctan) , cmap='RdBu')
	#c = ax.pcolor(QTTF.ACRES, cmap='RdBu', vmin = -4, vmax = 4)
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -2, vmax = 6)
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -3.5, vmax = 10)
	ax.set_title('Phase before rotation')
	fig2.colorbar(c, ax = ax)

	ax = axs2[2,1]
	c = ax.pcolor(QTTF.phasePlot, cmap='RdBu', vmin = 0, vmax = 180)
	#c = ax.pcolor(QTTF.ACRES, cmap='RdBu', vmin = -4, vmax = 4)
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -2, vmax = 6)
	#c = ax.pcolor(QTTF.ACdata, cmap='RdBu', vmin = -3.5, vmax = 10)
	ax.set_title('Phase after rotation')
	fig2.colorbar(c, ax = ax)

	plt.show()