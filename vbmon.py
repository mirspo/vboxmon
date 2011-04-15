#!/usr/bin/python

import time,sys,os

if sys.platform == 'win32' :
	win = True
	import win32com.client
else:
	win = False
	from vboxapi import VirtualBoxManager

UpdateInterval = 5
GraphTime = 60*5
if win :
	rrdpath = "c:\\test\\"
	rrdtool = 'c:\\test\\rrdtool\\rrdtool.exe'
else :
	rrdpath = '/home/ilya/test/2/rrd/'
	rrdtool = '/usr/bin/rrdtool'

MachineNameList = ['host']
colors = ['#F0F000','#FF0000','#00FF00','#0000FF','#F000F0','#383700','#A820ED','#13E0E0','#0C7474','#689430']
PicWidth = 500
PicHeight = 400
Debug = False

def GetVal(met_obj, Metric):
	if win :
		(values, names, objects, names_out, objects_out, units, scales, sequence_numbers,indices, lengths) = perf.QueryMetricsData([Metric], [met_obj])
		try:
			val = float(values[0]) / scales[0]
		except:  
			val = 0	
	else :
		met = perf.query([Metric],[met_obj])
		if len(met) == 0 or len(met[0]['values']) == 0 :
			val = 0
		else:
			val = int(float(met[0]['values'][0]/met[0]['scale']))
	return val

def GetValEx(met_obj, Pattern):
	vv = 0
	if win :
		mach = virtualBox.FindMachine(met_obj)
		state = mach.State
	else :
		mach = virtualBox.findMachine(met_obj)
		state = mach.state
	if state == 5:
		if win :
			mach.LockMachine(session,1)
			console = session.Console
			d = console.Debugger
			xml = d.GetStats(Pattern,True)
			session.UnlockMachine()
		else :
			mach.lockMachine(session,1)
			console = session.console
			d = console.debugger
			xml = d.getStats(Pattern,True)
			session.unlockMachine()
		
		lines =  xml.split('\n')
		vv = 0
		for line in lines:
			if line.find("<Counter") >= 0 :
				v = line.split()[1][3:-1]
				vv = vv + int(v)
	return vv

def GetMet(Machine, ShowValue):
	HasHost = Machine == 'host'
	rrdname = (rrdpath + Machine + '.rrd').replace(' ','_')
	if HasHost:
		met_obj = host
	else :
		if win :
			met_obj = virtualBox.FindMachine(Machine)
		else :
			met_obj = virtualBox.findMachine(Machine)

	if not os.access(rrdname,os.F_OK):
		s = rrdtool + " create " + rrdname + " --step 1" \
		" DS:Kernel:GAUGE:20:0:1000" \
		" DS:User:GAUGE:20:0:10000" \
		" DS:Idle:GAUGE:20:0:1000" \
		" DS:MEMUsed:GAUGE:20:0:10000000" \
		" DS:ReadBytes:COUNTER:20:0:U" \
		" DS:WrittenBytes:COUNTER:20:0:U" \
		" DS:ReceiveBytes:COUNTER:20:0:U" \
		" DS:TransmitBytes:COUNTER:20:0:U" \
		" RRA:LAST:0.5:1:10000" 
		os.system(s)
		if ShowValue:
			print s
	vk = GetVal(met_obj,'CPU/Load/Kernel')
	vu = GetVal(met_obj,'CPU/Load/User')
	vram = GetVal(met_obj,'RAM/Usage/Used')
	vi = 0
	
	if not HasHost :
		vir = GetValEx(Machine,'/Devices/*/ReadBytes')
		viw = GetValEx(Machine,'/Devices/*/WrittenBytes')
		vnr = GetValEx(Machine,'/Devices/*/ReceiveBytes')
		vnt = GetValEx(Machine,'/Devices/*/TransmitBytes')
	else :
		vir = 0 
		viw = 0
		vnr = 0
		vnt = 0 

	s = rrdtool + " update %s N:%d:%d:%d:%d:%d:%d:%d:%d"%(rrdname,vk,vu,vi,vram,vir,viw,vnr,vnt)
	os.system(s)
	if ShowValue:
		print s



def Graph(filename, Machines,times,metric,ShowValue, BeginN):
    s = rrdtool +' graph --start '+ str(int(time.time()) - times) +' --height ' + str(PicHeight) + ' --width ' + str(PicWidth) + ' -t "' + metric + '" '+ filename 
    n = BeginN + 1
    for m in Machines[BeginN:] :
        cn = metric + str(n)
        s = s + " DEF:" + metric + str(n) + "=" + rrdpath.replace(':','\:') + m.replace(' ','_') + '.rrd' + ':' + metric + ':LAST LINE1:' + cn + colors[n-1] + ':"' + m + '"'
        n = n + 1
    os.system(s)
    if ShowValue:
        print s

if win :
	virtualBox = win32com.client.Dispatch("VirtualBox.VirtualBox")
	host = virtualBox.Host
	perf = virtualBox.PerformanceCollector
	session = win32com.client.Dispatch("VirtualBox.Session")
	mList =  virtualBox.Machines 
else :
	vboxManager = VirtualBoxManager(None,None)
	virtualBox = vboxManager.vbox
	host = virtualBox.host
	perf = vboxManager.getPerfCollector(virtualBox)
	session = vboxManager.mgr.getSessionObject(vboxManager.vbox)
	mList = virtualBox.getMachines()

j = 1
for m in mList :
	if len(MachineNameList) >= len(colors) :
		colors.append(colors[j])
		j = j + 1
	MachineNameList.append(str(m.name))


while 1:
	if win :
		perf.SetupMetrics(None,None,UpdateInterval,1)
	else :
		perf.setup(None,None,UpdateInterval,1)
	time.sleep(float(UpdateInterval)+0.1)
	if Debug:
		print time.time()

	n = 0
	for m in MachineNameList :
		GetMet(m, Debug)

	Graph(rrdpath + 'test_user.png',MachineNameList,60*GraphTime,'User',Debug,0)
	Graph(rrdpath + 'test_kernel.png',MachineNameList,60*GraphTime,'Kernel',Debug,0)
	Graph(rrdpath + 'test_ram.png',MachineNameList,60*GraphTime,'MEMUsed',Debug,0)
	Graph(rrdpath + 'test_rio.png',MachineNameList,60*GraphTime,'ReadBytes',Debug,1)
	Graph(rrdpath + 'test_wio.png',MachineNameList,60*GraphTime,'WrittenBytes',Debug,1)
	Graph(rrdpath + 'test_TransmitBytes.png',MachineNameList,60*GraphTime,'TransmitBytes',Debug,1)
	Graph(rrdpath + 'test_ReceiveBytes.png',MachineNameList,60*GraphTime,'ReceiveBytes',Debug,1)
	if Debug :
		break

