#!/usr/bin/python

#histo
#catch add/delete vm list
#add RAM/Free counter
#add linux host net and io counter
#add exmach list for exclude vms

#todo
# win io and net counter 
# max,min,avg show value counter
# print values to console
# modify RRA to average 15m,1h,1d


version = 0.2

import time,sys,os
import ctypes
from ctypes import byref
from ctypes import Structure, Union
from ctypes.wintypes import *
import win32api
from ctypes import *
from _winreg import *

if sys.platform == 'win32' :
        win = True
        import win32com.client
        import win32api
        host_eth = '\DEVICE\TCPIP_{44D06796-5D02-4E15-A011-91070F6FDDD0}' #getmac
        host_disk = ''
else:
        win = False
        from vboxapi import VirtualBoxManager
        host_eth = 'eth0'       #ifconfig
        host_disk = 'sda,sdb,sr0' #ls /dev/hd?|sd?

UpdateInterval = 3
GraphTime = 60 * 1

colors = ['#F0F000','#FF0000','#00FF00','#0000FF','#F000F0','#383700','#A820ED','#13E0E0','#0C7474','#689430']
lines = ['','','','','','','','','','']
maxlines = len(lines)
exmach = 'test,uroute,xp sata,xpn1,centos'
PicWidth = 500
PicHeight = 400
Debug = False
MakeGraph = True
OnlyGraph = False

# other wintype definition
LPVOID = ctypes.c_void_p
LPCVOID = LPVOID
DWORD_PTR = DWORD
LONGLONG = ctypes.c_longlong
HCOUNTER = HQUERY = HANDLE

# error code
Error_Success = 0

# macro
sleep = ctypes.windll.kernel32.Sleep
pdh = ctypes.windll.pdh

# structure definition
class PDH_COUNTER_PATH_ELEMENTS(Structure): 
    _fields_ = [('szMachineName', LPVOID),
                ('szObjectName', LPVOID),
                ('szInstanceName', LPVOID),
                ('szParentInstance', LPVOID),
                ('dwInstanceIndex', DWORD),
                ('szCounterName', LPVOID)]

class Sysinfo_Struct(Structure):
    _fields_ = [('wProcessorArchitecture', WORD),
                ('wReserved', WORD)]

class Sysinfo_Union(Union):
    _fields_ = [('dwOemId', DWORD),
                ('struct', Sysinfo_Struct)]

class System_Info(Structure):
    _fields_ = [('union', Sysinfo_Union),
                ('dwPageSize', DWORD),
                ('lpMinimumApplicationAddress', LPVOID),
                ('lpMaximumApplicationAddress', LPVOID),
                ('dwActiveProcessorMask', DWORD_PTR),
                ('dwNumberOfProcessors', DWORD),
                ('dwProcessorType', DWORD),
                ('dwAllocationGranularity', DWORD),
                ('wProcessorLevel', WORD),
                ('wProcessorRevision', WORD)]

class PDH_Counter_Union(Union):
    _fields_ = [('longValue', LONG),
                ('doubleValue', ctypes.c_double),
                ('largeValue', LONGLONG),
                ('AnsiStringValue', LPCSTR),
                ('WideStringValue', LPCWSTR)]

class PDH_FMT_COUNTERVALUE(Structure):
    _fields_ = [('CStatus', DWORD),
                ('union', PDH_Counter_Union),]


WCHAR = wchar_t = c_ushort
BYTE = c_ubyte
SIZE_T = size_t = c_uint
ULONG = HANDLE = DWORD = c_ulong
NO_ERROR = 0
LPVOID = c_void_p

def STRING(size):
    class S(Array):
        _type_ = c_char
        _length_ = size

        def __str__(self):
            return "".join(self).split("\0")[0]

        def __repr__(self):
            return repr(str(self))

    return S

def WSTRING(size):
    class WS(Array):
        _type_ = wchar_t
        _length_ = size

        def __str__(self):
            return "".join(self).split("\0")[0]

        def __repr__(self):
            return repr(str(self))

    return WS

MAX_INTERFACE_NAME_LEN = 256
MAXLEN_IFDESCR = 256
MAXLEN_PHYSADDR = 8
MIB_IF_TYPE_LOOPBACK = 24
class MIB_IFROW(Structure):
#    _fields_ = [('wszName', c_wchar(MAX_INTERFACE_NAME_LEN)),
    _fields_ = [('wszName', c_wchar * MAX_INTERFACE_NAME_LEN),
                ('dwIndex', DWORD),
                ('dwType', DWORD),
                ('dwMtu', DWORD),
                ('dwSpeed', DWORD),
                ('dwPhysAddrLen', DWORD),
                ('bPhysAddr', STRING(MAXLEN_PHYSADDR)),
                ('dwAdminStatus', DWORD),
                ('dwOperStatus', DWORD),
                ('dwLastChange', DWORD),
                ('dwInOctets', DWORD),
                ('dwInUcastPkts', DWORD),
                ('dwInNUcastPkts', DWORD),
                ('dwInDiscards', DWORD),
                ('dwInErrors', DWORD),
                ('dwInUnknownProtos', DWORD),
                ('dwOutOctets', DWORD),
                ('dwOutUcastPkts', DWORD),
                ('dwOutNUcastPkts', DWORD),
                ('dwOutDiscards', DWORD),
                ('dwOutErrors', DWORD),
                ('dwOutQLen', DWORD),
                ('dwDescrLen', DWORD),
                ('bDesc', STRING(MAXLEN_IFDESCR))]

MAX_INTERFACES = 10
class MIB_IFTABLE(Structure):
    _fields_ = [('dwNumEntries', DWORD),
                ('table', MIB_IFROW * MAX_INTERFACES)]
#global variable
hQuery = HQUERY()
hCounter1 = HCOUNTER()
hCounter2 = HCOUNTER()
hCounter3 = HCOUNTER()
hCounter4 = HCOUNTER()
dwType = DWORD(0)
value = PDH_FMT_COUNTERVALUE()

#function
def GetCounterName(NumF,NumL):
    datasize1 = DWORD(1024)
    data1 = create_unicode_buffer(datasize1.value)
    dwRet = pdh.PdhLookupPerfNameByIndexW(None,NumF,byref(data1),byref(datasize1))

    datasize2 = DWORD(1024)
    data2 = create_unicode_buffer(datasize2.value)
    dwRet = pdh.PdhLookupPerfNameByIndexW(None,NumL,byref(data2),byref(datasize2))

    cn1 = ''.join(data1.value)
    cn2 = ''.join(data2.value)
    CounterName =  '\\' + cn1 + '(_Total)\\' + cn2
    return CounterName

def InitCounters():
    pdh.PdhOpenQueryW(None, 0, byref(hQuery))
    pdh.PdhAddCounterW(hQuery,GetCounterName(234,220),0,byref(hCounter3)) #read 
    pdh.PdhAddCounterW(hQuery,GetCounterName(234,222),0,byref(hCounter4)) #write

def DoneCounters():
    pdh.PdhCloseQuery(hQuery)

def ReadCounters():
    pdh.PdhCollectQueryData(hQuery)
    pdh.PdhGetFormattedCounterValue(hCounter3,0x00000100,byref(dwType),byref(value))
    v3 = value.union.longValue
    pdh.PdhGetFormattedCounterValue(hCounter4,0x00000100,byref(dwType),byref(value))
    v4 = value.union.longValue
    return v3,v4
    

if win :
        rrdpath = "e:\\test\\"
        rrdtool = 'C:\\Tools\\RRDtool\\rrdtool.exe'
else :
        rrdpath = '/home/ilya/test/2/rrd/'
        rrdtool = '/usr/bin/rrdtool'

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
        global PREV_IR
        global PREV_IW
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
                " DS:MEMUsed:GAUGE:20:0:U" \
                " DS:MEMFree:GAUGE:20:0:U" \
                " DS:ReadBytes:COUNTER:20:0:U" \
                " DS:WrittenBytes:COUNTER:20:0:U" \
                " DS:ReceiveBytes:COUNTER:20:0:U" \
                " DS:TransmitBytes:COUNTER:20:0:U" \
                " RRA:AVERAGE:0.5:1:1440 " \
                " RRA:AVERAGE:0.5:5:2016 " \
                " RRA:AVERAGE:0.5:60:720 " \
                " RRA:AVERAGE:0.5:3600:365"
                os.system(s)
                if ShowValue:
                        print s
        vk = GetVal(met_obj,'CPU/Load/Kernel')
        vu = GetVal(met_obj,'CPU/Load/User')
        vram = GetVal(met_obj,'RAM/Usage/Used') * 1024
        if HasHost:
                vramfree = GetVal(met_obj,'RAM/Usage/Free') * 1024
        else:
                vramfree = GetVal(met_obj,'Guest/RAM/Usage/Free') * 1024
        vi = 0
        
        if not HasHost :
                vir = GetValEx(Machine,'/Devices/*/ReadBytes')
                viw = GetValEx(Machine,'/Devices/*/WrittenBytes')
                vnr = GetValEx(Machine,'/Devices/*/ReceiveBytes')
                vnt = GetValEx(Machine,'/Devices/*/TransmitBytes')
        else :
                vnr = 0
                vnt = 0 
                vir = 0 
                viw = 0
                if not win :
                        f = open("/proc/net/dev")
                        all_lines = f.readlines()
                        f.close()               
                        for s in all_lines[2:]:
                                v = s.split()
                                e = str(v[0][:-1])
                                if host_eth.find(e) > -1 :
                                        vnr = vnr + int(v[1])
                                        vnt = vnt + int(v[9])
                        f = open("/proc/diskstats")
                        all_lines = f.readlines()
                        f.close()               
                        for s in all_lines:
                                v = s.split()
                                e = str(v[2])
                                if host_disk.find(e) > -1 :
                                        vir = vir + int(v[5])*512
                                        viw = viw + int(v[9])*512
                                        #print v
                else:
                        (vir,viw) = ReadCounters()
                        PREV_IR = PREV_IR + vir * UpdateInterval
                        PREV_IW = PREV_IW + viw * UpdateInterval
                        vir = PREV_IR
                        viw = PREV_IW
                        #print "IO r:", vir, 'w:', viw
                        for t in table.table:
                                res = windll.iphlpapi.GetIfTable(byref(table), byref(size), 0)
                                if host_eth.find(t.wszName):
                                        vnr = vnr + t.dwInOctets
                                        vnt = vnt + t.dwOutOctets
                        #print vnt,vnr,vir,viw

        s = rrdtool + " update %s N:%d:%d:%d:%d:%d:%d:%d:%d:%d"%(rrdname,vk,vu,vi,vram,vramfree,vir,viw,vnr,vnt)
        os.system(s)
        if ShowValue:
                print s



def Graph(filename, Machines,times,metric,ShowValue, BeginN):
        s = rrdtool +' graph --start '+ str(int(time.time()) - times) +' --height ' + str(PicHeight) + ' --width ' + str(PicWidth) + ' -t "' + metric + '" '+ filename 
        n = BeginN + 1
        for m in Machines[BeginN:] :
                cn = metric + str(n)
                s = s + " DEF:" + metric + str(n) + "=" + rrdpath.replace(':','\:') + m.replace(' ','_') + '.rrd' + ':' + metric + ':AVERAGE LINE1:' + cn + colors[n-1] + ':"' + m + '"'
#               s = s + " AREA:"+ cn + colors[n-1]+":LAST
                s = s + " GPRINT:"+ cn +":LAST:'Last%8.2lf%s' " 
                s = s + " GPRINT:"+ cn +":AVERAGE:'AVG%8.2lf%s' GPRINT:"+cn+":MAX:'Max%8.2lf%s' GPRINT:"+cn+":MIN:'MIN%8.2lf%s' "
                n = n + 1
        if not win:
                s = s + " > /dev/null"
        os.system(s)
        if ShowValue:
                print s

def UpdateList():
        MachineNameList = ['host']
        if win :
                mList =  virtualBox.Machines 
        else :
                mList = virtualBox.getMachines()

        j = 1
        l = 1
        for m in mList :
                if exmach.find(str(m.name)) > -1 :
                        continue
                if len(MachineNameList) >= len(colors) :
                        colors.append(colors[j])
                        j = j + 1
                        if l > maxlines : 
                                maxlines = maxlines * 2
                                l = l + 1
                        lines.append(str(l))
                MachineNameList.append(str(m.name))
        return MachineNameList
        

PREV_IR = 0
PREV_IW = 0

if win :
        virtualBox = win32com.client.Dispatch("VirtualBox.VirtualBox")
        host = virtualBox.Host
        perf = virtualBox.PerformanceCollector
        session = win32com.client.Dispatch("VirtualBox.Session")
        table = MIB_IFTABLE()
        size = ULONG(sizeof(table))
        table.dwNumEntries = 0
        res = windll.iphlpapi.GetIfTable(byref(table), byref(size), 0)
        if res == 122:
                resize(table,size.value)
                
                
        res = windll.iphlpapi.GetIfTable(byref(table), byref(size), 0)
else :
        vboxManager = VirtualBoxManager(None,None)
        virtualBox = vboxManager.vbox
        host = virtualBox.host
        perf = vboxManager.getPerfCollector(virtualBox)
        session = vboxManager.mgr.getSessionObject(vboxManager.vbox)

while 1:
        if Debug:
                print time.time()
        MachineNameList = UpdateList()
        if not OnlyGraph :
                if win :
                        perf.SetupMetrics(None,None,UpdateInterval,1)
                        InitCounters()
                        ReadCounters()
                else :
                        perf.setup(None,None,UpdateInterval,1)
                time.sleep(float(UpdateInterval)+0.1)
                for m in MachineNameList:
                        GetMet(m, Debug)
                if win:
                        DoneCounters()
        if MakeGraph or OnlyGraph:
                Graph(rrdpath + 'test_user.png',MachineNameList,60*GraphTime,'User',Debug,0)
                Graph(rrdpath + 'test_kernel.png',MachineNameList,60*GraphTime,'Kernel',Debug,0)
                Graph(rrdpath + 'test_ram.png',MachineNameList,60*GraphTime,'MEMUsed',Debug,0)
                Graph(rrdpath + 'test_ramfree.png',MachineNameList,60*GraphTime,'MEMFree',Debug,0)
                Graph(rrdpath + 'test_rio.png',MachineNameList,60*GraphTime,'ReadBytes',Debug,0)
                Graph(rrdpath + 'test_wio.png',MachineNameList,60*GraphTime,'WrittenBytes',Debug,0)
                Graph(rrdpath + 'test_TransmitBytes.png',MachineNameList,60*GraphTime,'TransmitBytes',Debug,0)
                Graph(rrdpath + 'test_ReceiveBytes.png',MachineNameList,60*GraphTime,'ReceiveBytes',Debug,0)
        if OnlyGraph :
                break

