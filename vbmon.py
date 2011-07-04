#!/usr/bin/python
"""VirtualBox performance monitoring. Version 0.3

Usage:
vbmon.py -h -v -i <sec> -d <path> -s <sec>
    -p  display setting parameters only    
    -h  print help
    -v  display debug message
    -i  interval take mesure in seconds, default 10
    -d  path to save rrd and image files
    -s  timeline length graphics in minutes, default 30
    -e  exclude VMs, coma separator, default all
    -x  width picture, default 450
    -y  heigth picture, default 300
    -g  make picture, default false
    -c  only make picture
    -r  rrdtool path, default vbmon.py directory 
    -b  hard disk, coma separate, default 'sda,sdb,sr0' (for windows only all)
    -n  net device,coma separate, default 'eth0' (for windows unknow)
    -m  not make host graph, default False
"""

import time,sys,os
import ctypes
from ctypes import byref
from ctypes import Structure, Union

if sys.platform == 'win32' :
        win = True
        import win32com.client
        import win32api
        from ctypes.wintypes import *
        from ctypes import *
        from _winreg import *
        host_eth = '\DEVICE\TCPIP_{44D06796-5D02-4E15-A011-91070F6FDDD0},\Device\Tcpip_{99339252-11E7-4F88-AB53-262C8B4407EF}' #getmac
        host_disk = ''
        rrdpath = "e:\\test\\"
        rrdtool = 'C:\\Tools\\RRDtool\\rrdtool.exe'
else:
        win = False
        from vboxapi import VirtualBoxManager
        host_eth = 'eth0'       #ifconfig
        host_disk = 'sda,sdb,sr0' #ls /dev/hd?|sd?
        rrdpath = '/home/ilya/test/2/rrd/'
        rrdtool = '/usr/bin/rrdtool'

UpdateInterval = 10
GraphTime = 1 * 30


global PrevValue
PrevValue = []

colors = ['#F0F000','#FF0000','#00FF00','#0000FF','#F000F0','#383700','#A820ED','#13E0E0','#0C7474','#689430']
exmach = ''
PicWidth = 450
PicHeight = 300

lines = ['','','','','','','','','','']
maxlines = len(lines)
Debug = False
MakeGraph = False
OnlyGraph = False
HostGraph = True

def ValueToStr(Val):
        if Val == None:
                Val = 'U'
        else:
                Val = str(Val)
        return Val

def DisplayParam():
        print 'vbmon running.'
        print ' -v Debug mode',Debug
        print ' -d datapath',rrdpath
        print ' -r rrdpath',rrdtool
        print ' -i update interval',UpdateInterval
        print ' -s time length',GraphTime
        print ' -x picture width:',PicWidth
        print ' -y picture height:',PicHeight
        print ' -g make picture:',MakeGraph
        print ' -c make picture only:',OnlyGraph
        print ' -n eth:',host_eth
        print ' -b disk:',host_disk
        print ' -e vn exclude:',exmach
        print ' -m Host graph:',HostGraph

if win:
    # other wintype definition
    LPVOID = ctypes.c_void_p
    LPCVOID = LPVOID
    DWORD_PTR = DWORD
    LONGLONG = ctypes.c_longlong
    HCOUNTER = HQUERY = HANDLE

    # error code
    #Error_Success = 0

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
    

def GetVal(met_obj, Metric, Mult):
        if win :
                (values, names, objects, names_out, objects_out, units, scales, sequence_numbers,indices, lengths) = perf.QueryMetricsData([Metric], [met_obj])
                try:
                        val = float(values[0]) / scales[0]
                except:  
                        val = None
        else :
                met = perf.query([Metric],[met_obj])
                if len(met) == 0 or len(met[0]['values']) == 0 :
                        val = None
                else:
                        val = int(float(met[0]['values'][0]/met[0]['scale']))
        if val <> None:
                val = val * Mult
        return val

                     
def GetValEx(met_obj, Pattern):
        vv = None
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
                for line in lines:
                        if line.find("<Counter") >= 0 :
                                v = line.split()[1][3:-1]
                                if vv == None:
                                        vv = int(v)
                                else:
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
                " DS:ReadBytes:GAUGE:20:0:U" \
                " DS:WrittenBytes:GAUGE:20:0:U" \
                " DS:ReceiveBytes:COUNTER:20:0:U" \
                " DS:TransmitBytes:COUNTER:20:0:U" \
                " RRA:AVERAGE:0.5:1:1440 " \
                " RRA:AVERAGE:0.5:5:2016 " \
                " RRA:AVERAGE:0.5:60:720 " \
                " RRA:AVERAGE:0.5:3600:365"
                os.system(s)
                if ShowValue:
                        print s
        vk = GetVal(met_obj,'CPU/Load/Kernel',1)
        vu = GetVal(met_obj,'CPU/Load/User',1)
        vram = GetVal(met_obj,'RAM/Usage/Used',1024)
        if HasHost:
                vramfree = GetVal(met_obj,'RAM/Usage/Free',1024)
        else:
                vramfree = GetVal(met_obj,'Guest/RAM/Usage/Free',1024)
        vi = 0
        
        if not HasHost :
                i = MachineNameList.index(Machine)

                tvir = GetValEx(Machine,'/Devices/*/ReadBytes')
                tviw = GetValEx(Machine,'/Devices/*/WrittenBytes')

                if PrevValue[i][0] <> None and tvir <> None:
                        vir = (tvir - PrevValue[i][0]) / UpdateInterval
                else:
                        vir = None
                if PrevValue[i][1] <> None and tviw <> None:
                        viw = (tviw - PrevValue[i][1]) / UpdateInterval
                else:
                        viw = None
                PrevValue[i][0] = tvir
                PrevValue[i][1] = tviw

                #bugs in VB?
                vnr = GetValEx(Machine,'/Devices/*/ReceiveBytes')
                vnr_virtio = GetValEx(Machine,'/Devices/*/Bytes/Receive')
                if vnr == None:
                        vnr = vnr_virtio
                else: 
                        if vnr_virtio <> None:
                                vnr = vnr + vnr_virtio
                    
                vnt = GetValEx(Machine,'/Devices/*/TransmitBytes')
                vnt_virtio = GetValEx(Machine,'/Devices/*/Bytes/Transmit')
                if vnt == None:
                        vnt = vnt_virtio
                else: 
                        if vnt_virtio <> None:
                                vnt = vnt + vnt_virtio
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
                        tvir = 0
                        tviw = 0
                        for s in all_lines:
                                v = s.split()
                                e = str(v[2])
                                if host_disk.find(e) > -1 :
                                        tvir = tvir + int(v[5])*512
                                        tviw = tviw + int(v[9])*512

                        if PrevValue[0][0] <> None and tvir <> None:
                                vir = (tvir - PrevValue[0][0]) / UpdateInterval
                        else:
                                vir = None
                        if PrevValue[0][1] <> None and tviw <> None:
                                viw = (tviw - PrevValue[0][1]) / UpdateInterval
                        else:
                                viw = None
                        PrevValue[0][0] = tvir
                        PrevValue[0][1] = tviw

                else:
                        (vir,viw) = ReadCounters()
                        for t in table.table:
                                res = windll.iphlpapi.GetIfTable(byref(table), byref(size), 0)
                                if host_eth.find(t.wszName):
                                        vnr = vnr + t.dwInOctets
                                        vnt = vnt + t.dwOutOctets
                

        s = rrdtool + " update %s N:%s:%s:%s:%s:%s:%s:%s:%s:%s"%(rrdname,ValueToStr(vk),ValueToStr(vu),ValueToStr(vi),ValueToStr(vram),ValueToStr(vramfree),ValueToStr(vir),ValueToStr(viw),ValueToStr(vnr),ValueToStr(vnt))
        os.system(s)
        if ShowValue:
                print s



def Graph(filename, Machines,times,metric,ShowValue, BeginN):
        s = rrdtool +' graph --start '+ str(int(time.time()) - times) +' --height ' + str(PicHeight) + ' --width ' + str(PicWidth) + ' -t "' + metric + '" '+ filename
        n = BeginN + 1
        for m in Machines[BeginN:] :
                if not HostGraph and m == 'host' :
                    continue
                cn = metric + str(n)
                s = s + " DEF:" + metric + str(n) + "=" + rrdpath.replace(':','\:') + m.replace(' ','_') + '.rrd' + ':' + metric + ':AVERAGE LINE1:' + cn + colors[n-1] + ':"' + m + '"'
                s = s + " GPRINT:"+ cn +":LAST:'Last%8.2lf%s' "
                s = s + " GPRINT:"+ cn +":AVERAGE:'AVG%8.2lf%s' GPRINT:"+cn+":MAX:'Max%8.2lf%s' GPRINT:"+cn+":MIN:'MIN%8.2lf%s' "
                n = n + 1
        if not win:
                s = s + " > /dev/null"
        else:
                s = s + " > nul"
        os.system(s)
        if ShowValue:
                print s

def UpdateList(maxlines):
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
        

def Usage(ErrorCode):
        print __doc__
        sys.exit(ErrorCode)

argv = sys.argv[1:]
try:
    #bad code. need to do nice :)
        i = 0
        while i < len(argv):
                if argv[i] == '-c':
                        OnlyGraph = True
                        i = i + 1
                        continue
                if argv[i] == '-y':
                        PicHeight = int(argv[i+1])
                        i = i + 2
                        continue
                if argv[i] == '-x':
                        PicWidth = int(argv[i+1])
                        i = i + 2
                        continue
                if argv[i] == '-g':
                        MakeGraph = True
                        i = i + 1
                        continue
                if argv[i] == '-p':
                        DisplayParam()
                        sys.exit(0)
                        continue
                if argv[i] == '-h':
                        i = i + 1
                        Usage(0)
                if argv[i] == '-v':
                        Debug = True
                        i = i + 1
                        continue
                if argv[i] == '-i':
                        UpdateInterval = int(argv[i+1])
                        i = i + 2
                        continue
                if argv[i] == '-s':
                        GraphTime = int(argv[i+1])
                        i = i + 2
                        continue
                if argv[i] == '-d':
                        Path = argv[i+1]
                        i = i + 2
                        continue
                if argv[i] == '-m':
                        HostGraph = False
                        i = i + 1
                        continue                
                if argv[i] == '-r':
                        rrdpath = argv[i+1]
                        i = i + 2
                        continue
                if argv[i] == '-b':
                        host_disk = argv[i+1]
                        i = i + 2
                        continue
                if argv[i] == '-e':
                        exmach = argv[i+1]
                        i = i + 2
                        continue
                if argv[i] == '-n':
                        host_eth = argv[i+1]
                        i = i + 2
                        continue
                print 'Bad argument:',argv[i]
                Usage(2)
        
except Exception as err:
        print err
        Usage(2)

if Debug:
        DisplayParam()

PREV_IR = None
PREV_IW = None

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

#to minutes
GraphTime = GraphTime * 60

while 1:
        if Debug:
                print time.time()
        MachineNameList = UpdateList(maxlines)
        while len(PrevValue) < len(MachineNameList):
                PrevValue.append([-1,-1])
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
                Graph(rrdpath + 'test_user.png',MachineNameList,GraphTime,'User',Debug,0)
                Graph(rrdpath + 'test_kernel.png',MachineNameList,GraphTime,'Kernel',Debug,0)
                Graph(rrdpath + 'test_ram.png',MachineNameList,GraphTime,'MEMUsed',Debug,0)
                Graph(rrdpath + 'test_ramfree.png',MachineNameList,GraphTime,'MEMFree',Debug,0)
                Graph(rrdpath + 'test_rio.png',MachineNameList,GraphTime,'ReadBytes',Debug,0)
                Graph(rrdpath + 'test_wio.png',MachineNameList,GraphTime,'WrittenBytes',Debug,0)
                Graph(rrdpath + 'test_TransmitBytes.png',MachineNameList,GraphTime,'TransmitBytes',Debug,0)
                Graph(rrdpath + 'test_ReceiveBytes.png',MachineNameList,GraphTime,'ReceiveBytes',Debug,0)
        if OnlyGraph :
                break
