 # -*- coding: utf-8 -*-   
#qpy:kivy

from kivy import require
require('1.9.0') # replace with your current kivy version !
from kivy.properties import StringProperty, ObjectProperty, ListProperty, NumericProperty 
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.clock import Clock
from kivy.app import App
from kivy.lang import Builder
from kivy.garden.graph import Graph, MeshLinePlot
from kivy.uix.boxlayout import BoxLayout
import mysql.connector
import threading
import datetime
import time

# GLOBAL VARIABLES HERE:
localhost = 'fuelcelldb.mysqldb.chinacloudapi.cn' # Server eg: localhost
dbname    = 'fuelcelldb' # SQL Database Name.
dbuser    = 'fuelcelldb%junge8830' # SQL Database Username.
dbpw      = 'junGE8830' # SQL Database Password.
tablename = 'parameters' # SQL Table name here.
ConnFlag = 0
descripID = {'ID':0, 'voltage':1, 'current':2, 'temperature':3, 'timestamp':4}

RASPBERRYPI_NAME = 'raspberrypi'

global realtimegraph, rtgraphupdate, MeasureRTPlot, Outdata
realtimegraph = None
rtgraphupdate = None
global MeasureRTPlotValue # for realtimegraph measurement line value
MeasureRTPlotValue = None
Outdata = []
# for offline graph measurement line value
global offlinegraph, MeasurePlotValue
offlinegraph = None
MeasurePlotValue = None

class ConnThreading(threading.Thread):
    """
    Thread to connection to database in the background without
    disturbing user interface.
    """
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
    def run(self):
        print ("Starting " + self.name)
        global conn, cursor, ConnFlag
        try:
            conn = mysql.connector.connect(host=localhost,
                                  database=dbname,
                                  user=dbuser,
                                  password=dbpw)
            cursor = conn.cursor()
            ConnFlag = 1 # Set Connection Flag to 1, succeed so other function can be alerted.
            print ("DB connected successfully! Exiting " + self.name)
        except mysql.connector.Error as e:
            print("Connection fail, Error Code: \n",e)
            # quit()
            # Codes to save to log file here
class PromptSuccess(threading.Thread):
    """
    Thread to check the ConnThreading for connection completeness
    and to give return message to the displaytext input argument.
    """
    def __init__(self, threadID, name, threadtojoin, displaytext):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.displaytext = displaytext
        self.threadtojoin = threadtojoin
    def run(self):
        print ("Starting " + self.name)
        self.threadtojoin.join()
        self.displaytext.text = "If there is no data,please contact the author's mailbox zejunwen@qq.com!"






#### Individual Screen/Page coding Starts here:
############################## LOGIN SCREEN ################################
class LoginScreen(Screen):
    def new_login_try(self, username, password, displaytext):
        payload = ("admin", "cqufcv")         #Real Credentials
        displaytext.text = "Logging in ..."
        ErrorType = "Please key in your username and password."
        print("Username Keyed: {}, Password Keyed: {}".format(username.text, password.text))
        try:
            if username.text == "" and password.text == "":
                ErrorType = "No credentials keyed in."
                raise
            if username.text.lower() == payload[0]:
                pass
            else:
                ErrorType = "Wrong Credentials!"
                raise 
            if password.text == payload[1]:
                print("Login Success!")
                displaytext.text = "Success! Please wait.."
                username.text = ""
                password.text = ""
                
                global connthread
                connthread = ConnThreading(1, "DBconnectThread")
                connthread.start()
                self.manager.current = "IndexScreen"
                displaytext.text = ""
            else:
                ErrorType = "Wrong Credentials!"
                raise
        except:
##            try:
##                from jnius import autoclass
##                displaytext.text = "Success in importing jnius!"
##            except:
##                displaytext.text = ErrorType
                      
            # For bypass troubleshooting purposes:
            #global connthread
            #connthread = ConnThreading(1, "DBconnectThread")
            #connthread.start()
            #self.manager.current = "IndexScreen"
            displaytext.text = ErrorType
            

            

############################## INDEX SCREEN ################################
class IndexScreen(Screen):
    transactionsn = StringProperty('')              #Storing Data In IndexScreen
    transactiontype = ListProperty('')

    def signout(self):
        self.manager.current = "LoginScreen"
        try:
            rtgraphupdate.event.set()
            rtgraphupdate.join()
        except:
            pass
        global ConnFlag
        ConnFlag = 0
        conn.close()

        
######################## REALTIME MEASUREMENT SCREEN #######################
class RealTimeMeasurement(Screen):
    def start(self, displaytext, graph, param, xlabel, ylabel):
        xlabel.text = "None"
        ylabel.text = "None"
        global realtimegraph
        global SelectedDate, SortID, rtgraphupdate
        try:
            rtgraphupdate.event.set()
            rtgraphupdate.join()
        except:
            pass

        SelectedDate=datetime.datetime.now().date()
        try:
            SortID = descripID[(param.text[20:]).lower()]
        except:
            displaytext.text = "Choose the parameter from the dropdown box!"
            return

        if realtimegraph is None:
            global MeasureRTPlot, plot
            realtimegraph = graph
            plot = MeshLinePlot(color=[1, 1, 0, 1])
            MeasureRTPlot = MeshLinePlot(color=[1,0,0,1]) #For the marker
            realtimegraph.add_plot(plot)
            realtimegraph.add_plot(MeasureRTPlot)

        if not ConnFlag:
            displaytext.text = "Please hold. Connecting to database..."
            prompter = PromptSuccess(1, "PrompterConnection", connthread, displaytext)
            prompter.start()
            return            
        global realtimedata
        realtimedata = self.SQL_select_data_date(SelectedDate)
        #print(realtimedata)    
        if not realtimedata:
            displaytext.text = "Data is empty for date: "+str(SelectedDate)
            print("Data is empty for date: ", SelectedDate)
            return
        
        # data will result in [(minutes, param),(minutes, param),(minutes, param)]
        global Outdata, ymin, ymax, xmin, xmax
        Outdata, ymin, ymax, xmin, xmax = self.dataConvert(realtimedata, SortID, 100)

        # Set initial graph axis to suit data
        realtimegraph.xmin = xmin
        realtimegraph.ymin = ymin
        realtimegraph.xmax = xmax
        realtimegraph.ymax = ymax
        realtimegraph.ylabel = param.text[20:]

        # Plot plot1 with the given data as points
        displaytext.text = " "
        plot.points = Outdata

        try:
            rtgraphupdate.event.set()
            rtgraphupdate.join()
        except:
                pass
        rtgraphupdate = RTGraphUpdateThread(1, "RTGraphUpdate", realtimegraph, plot, 0.5)
        rtgraphupdate.start()
            
    def stop(self):
        try:
            rtgraphupdate.event.set()
        except:
            print("no update thread to stop.")
        
    def setdefault(self, ylabel_measure, xlabel_measure, paramselect):
        try:
            rtgraphupdate.event.set()
        except:
            pass
        global realtimegraph, Outdata, plot
        try:
            plot.points = [(0,0)]
            MeasureRTPlot.points = [(0,0)]
        except:
            pass
        realtimegraph = None
        Outdata = []
        ylabel_measure.text = "None"
        xlabel_measure.text = "None"
        paramselect.text = "Press here to select the parameters"

    def SQL_select_data_date(self, date):
        ''' Select specific set of data from the sql param_trial table where
            the timestamp column is the given arg date (in timestamp format)
        '''
        nextday = date + datetime.date.resolution
        Select_Command = "select * from "+tablename+" where timestamp >= %s and timestamp < %s"
        args = (date, nextday)
        cursor.execute(Select_Command, args)
        data = cursor.fetchall()
        return data

    def dataConvert(self, data, SortID, limit_size):
        ''' Converts the SQL data into [(minutes, param),(minutes, param),(minutes, param)]
            format, returns output, ymin, ymax for the graph
            ## Shortcut:
            ## data = [(data[x][-1].hour*60+data[x][-1].minute, data[x][SortID]) for x in range(0, len(data))]
        '''
        Indata = data[-limit_size:] # this limit the amt of data (in range of Latest amt)
        Outdata = []
        ymin = Indata[0][SortID]
        ymax = Indata[0][SortID]
        for x in range(0,len(Indata)):
            output = round(float(Indata[x][SortID]), 2)
            hour = float(Indata[x][-1].hour*60)
            minute = float(Indata[x][-1].minute)
            second = round(float(Indata[x][-1].second)/60, 2)
            time = hour + minute + second
            Outdata.append((time, output))
            if output > ymax:
                ymax=output
            if output < ymin:
                ymin=output
            if x is 0:
                xmin = round(time,2)
            if x is (len(Indata)-1):
                xmax = round(time,2)
        if len(Indata) is 1:
            xmax = xmin+99
            ymax = ymin+1
        elif xmax-100 > xmin:
            xmin = xmax-100
            
        return Outdata, ymin, ymax, xmin, xmax

    def Display_value(self, option, xlabel, ylabel, troublshoot_label):
        """
        requires global plot: MeasureRTPlot
        """
        global MeasureRTPlotValue
        from collections import OrderedDict
        DictOutdata = OrderedDict(Outdata)
        #troublshoot_label.text = str(DictOutdata)
        if not Outdata:
            return
        if xlabel.text == "None": #first run
            if option == 1:
                count = 0
                while True:
                    MeasureRTPlotValue = Outdata[count]
                    if xmin > MeasureRTPlotValue[0]:
                        count=count+1
                    else:
                        break
                MeasureRTPlot.points = [(MeasureRTPlotValue[0] , ymin), MeasureRTPlotValue, (MeasureRTPlotValue[0], ymax)]
                #xlabel.text = str(MeasureRTPlotValue[0])
                ylabel.text = str(MeasureRTPlotValue[1])
                m,s = divmod(MeasureRTPlotValue[0]*60,60)
                h,m = divmod(m,60)
                xlabel.text = "%02d:%02d:%02d" % (h,m,round(s))
                return
            
        if option == 1:
            # Next Value:
            nextindex = list(DictOutdata.keys()).index(MeasureRTPlotValue[0])+1
            print(nextindex)
            if nextindex > len(Outdata)-1:
                return
            else:
                MeasureRTPlotValue = Outdata[nextindex]
                MeasureRTPlot.points = [(MeasureRTPlotValue[0] , ymin), MeasureRTPlotValue, (MeasureRTPlotValue[0], ymax)]
                #xlabel.text = str(MeasureRTPlotValue[0])
                ylabel.text = str(MeasureRTPlotValue[1])
                m,s = divmod(MeasureRTPlotValue[0]*60,60)
                h,m = divmod(m,60)
                xlabel.text = "%02d:%02d:%02d" % (h,m,round(s))
                
        if option == -1:
            # Next Value:
            previndex = list(DictOutdata.keys()).index(MeasureRTPlotValue[0])-1
            if previndex < 0:
                return
            elif Outdata[previndex][0] < xmin:
                return
            else:
                MeasureRTPlotValue = Outdata[previndex]
                MeasureRTPlot.points = [(MeasureRTPlotValue[0] , ymin), MeasureRTPlotValue, (MeasureRTPlotValue[0], ymax)]
                #xlabel.text = str(MeasureRTPlotValue[0])
                ylabel.text = str(MeasureRTPlotValue[1])
                m,s = divmod(MeasureRTPlotValue[0]*60,60)
                h,m = divmod(m,60)
                xlabel.text = "%02d:%02d:%02d" % (h,m,round(s))

class RTGraphUpdateThread(threading.Thread):
    def __init__(self, threadID, name, rtgraph, plot, time):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.rtgraph = rtgraph
        self.plot = plot
        self.time = time
        self.event = threading.Event()
    def run(self):
        if not ConnFlag:
            print("Database not connected!")
            return
        print ("Starting " + self.name)
        while not self.event.is_set():
            time.sleep(self.time) #delay between update interval in seconds
            global realtimedata, Outdata, ymin, ymax, xmin, xmax #Need: SortID, cursor, conn

            ID = realtimedata[-1][0] #obtain the last obtained data ID
            print("Last ID: ",ID)

            now = SelectedDate
            tmr = now + datetime.date.resolution
            args = (now, tmr)
            
            Select_Command = "select * from "+tablename+" where timestamp >= %s and timestamp < %s and id > "+str(ID)
            #Select should NOT take more than 100x data cus UPDATE FUNCTION, but will still be taken care in dataConvert
            cursor.execute(Select_Command, args)
            row = cursor.fetchall()
            print("New data: ", row)

            realtimedata = realtimedata + row
            if len(realtimedata) is 1:
                self.plot.points = Outdata
                conn.commit()
                continue
            Outdata, Outymin, Outymax, Outxmin, Outxmax = self.dataConvert(realtimedata, SortID, 100)

            if Outymin < ymin:
                self.rtgraph.ymin = Outymin
                ymin = Outymin
            if Outymax > ymax:
                self.rtgraph.ymax = Outymax
                ymax = Outymax

            if Outxmin < xmin:
                self.rtgraph.xmin = Outxmin
                xmin = Outxmin
            if Outxmax > xmax:
                self.rtgraph.xmax = Outxmax
                xmax = Outxmax
            if (Outxmax - Outxmin) > 1000:
                self.rtgraph.x_ticks_major = 240
            elif (Outxmax - Outxmin) > 100:
                self.rtgraph.x_ticks_major = 50
            elif (Outxmax - Outxmin) > 10:
                self.rtgraph.x_ticks_major = 5
                

            # Plot plot1 with the given data as points
            self.plot.points = Outdata
            conn.commit()

    
    def dataConvert(self, data, SortID, limit_size):
        ''' Converts the SQL data into [(minutes, param),(minutes, param),(minutes, param)]
            format, returns output, ymin, ymax for the graph
            ## Shortcut:
            ## data = [(data[x][-1].hour*60+data[x][-1].minute, data[x][SortID]) for x in range(0, len(data))]
        '''
        Indata = data[-limit_size:] # this limit the amt of data (in range of Latest amt)
        Outdata = []
        ymin = Indata[0][SortID]
        ymax = Indata[0][SortID]
        for x in range(0,len(Indata)):
            output = round(float(Indata[x][SortID]), 2)
            hour = float(Indata[x][-1].hour*60)
            minute = float(Indata[x][-1].minute)
            second = round(float(Indata[x][-1].second)/60, 2)
            time = hour + minute + second
            Outdata.append((time, output))
            if output > ymax:
                ymax=output
            if output < ymin:
                ymin=output
            if x is 0:
                xmin = round(time,2)
            if x is (len(Indata)-1):
                xmax = round(time,2)
        if len(Indata) is 1:
            xmax = xmin+99
            ymax = ymin+1
        elif xmax-100 > xmin:
            xmin = xmax-100
            
        return Outdata, ymin, ymax, xmin, xmax
            


######################## OFFLINE MONITORING SCREEN #########################
class OfflineMonitoring(Screen):
    def start(self, displaytext, graph, year, month, day, param, xlabel, ylabel):
        xlabel.text = "None"
        ylabel.text = "None"
        try:
            if year.text=="":
                SelectedDate=datetime.datetime.now().date()
                year.text = str(SelectedDate.year)
                month.text = str(SelectedDate.month)
                day.text = str(SelectedDate.day)
            else:
                SelectedDate = datetime.date(int(str(year.text)), int(str(month.text)), int(str(day.text)))
                print(SelectedDate)
        except:
            displaytext.text = "Date is in wrong format!"
            print("Date is in wrong format!")
            return
        try:
            SortID = descripID[(param.text[20:]).lower()]
            print(SortID)
        except:
            displaytext.text = "Choose the parameter from the dropdown box!"
            return

        global MeasurePlot, offlinegraph
        if offlinegraph is None:
            global plot, MeasurePlot
            plot = MeshLinePlot(color=[1, 1, 0, 1])
            MeasurePlot = MeshLinePlot(color=[1,0,0,1]) #For the marker
            graph.add_plot(plot)
            graph.add_plot(MeasurePlot)
        else:
            print("Clearing..")
            plot.points = [(0,0)]

        if not ConnFlag:
            displaytext.text = "Please hold. Connecting to database..."
            prompter = PromptSuccess(1, "PrompterConnection", connthread, displaytext)
            prompter.start()
            return            
        acquireddata = self.SQL_select_data_date(SelectedDate)
        #print(acquireddata)
            
        if not acquireddata:
            displaytext.text = "Data is empty for date: "+str(SelectedDate)
            print("Data is empty for date: ", SelectedDate)
            return
        
        # data will result in [(minutes, param),(minutes, param),(minutes, param)]
        global Outdata
        #Outdata, ymin, ymax, xmin, xmax = self.fulldataConvert(acquireddata, SortID)
        Outdata, ymin, ymax = self.fulldataConvert(acquireddata, SortID)

        # Set initial graph axis to suit data
        graph.xmin = 0 #xmin
        graph.ymin = ymin
        graph.xmax = 24*60 #xmax
        graph.ymax = ymax
        graph.ylabel = param.text[20:]

        # Plot plot1 with the given data as points
        displaytext.text = " "
        plot.points = Outdata
    def stop(self):
        try:
            rtgraphupdate.event.set()
        except:
            print("no update thread to stop.")        
        
    def setdefault(self, ylabel_measure, xlabel_measure, paramselect, displaytext):
        try:
            rtgraphupdate.event.set()
        except:
            pass
        global realtimegraph, Outdata, plot
        try:
            plot.points = [(0,0)]
            MeasurePlot.points = [(0,0)]
        except:
            print("Failed at clearing plots.")
            pass
        realtimegraph = None
        Outdata = []
        displaytext.text = ""
        ylabel_measure.text = "None"
        xlabel_measure.text = "None"
        paramselect.text = 'Press here to select the parameters'

    def SQL_select_data_date(self, date):
        ''' Select specific set of data from the sql param_trial table where
            the timestamp column is the given arg date (in timestamp format)
        '''
        nextday = date + datetime.date.resolution
        Select_Command = "select * from "+tablename+" where timestamp >= %s and timestamp < %s"
        args = (date, nextday)
        cursor.execute(Select_Command, args)
        data = cursor.fetchall()
        return data

    def fulldataConvert(self, Indata, SortID):
        ''' Converts the SQL data into [(minutes, param),(minutes, param),(minutes, param)]
            format, returns output, ymin, ymax for the graph
            ## Shortcut:
            ## data = [(data[x][-1].hour*60+data[x][-1].minute, data[x][SortID]) for x in range(0, len(data))]
        '''
        Outdata = []
        ymin = Indata[0][SortID]
        ymax = Indata[0][SortID]
        #print(len(Indata)-1)
        for x in range(0,len(Indata)):
            output = round(float(Indata[x][SortID]), 2)
            hour = float(Indata[x][-1].hour*60)
            minute = float(Indata[x][-1].minute)
            second = round(float(Indata[x][-1].second)/60, 2)
            time = hour + minute + second
            Outdata.append((time, output))
            if output > ymax:
                ymax=output
            if output < ymin:
                ymin=output
            if x is 0:
                xmin = round(time,2)
                #print(time)
            if x is (len(Indata)-1):
                xmax = round(time,2)
                #print(time)
                #print(xmax)
            #print(x)    
        if len(Indata) is 1:
            xmax = xmin+99
            ymax = ymin+1
        #elif xmax-100 > xmin:
         #   xmin = xmax-100
        
        #print(Outdata,ymin,ymax,xmin,xmax)        
        #return Outdata, ymin, ymax, xmin, xmax
        return Outdata, ymin, ymax
    
    def Display_value(self, option, graph2, xlabel, ylabel, troublshoot_label):
        """
        requires global plot: MeasurePlot
        """
        global MeasurePlotValue
        from collections import OrderedDict
        DictOutdata = OrderedDict(Outdata)
        #troublshoot_label.text = str(DictOutdata)
        if not Outdata:
            return
        if xlabel.text == "None": #first run
            if option == 1:
##                count = 0
##                while True:
##                    MeasurePlotValue = Outdata[count]
##                    if xmin > MeasurePlotValue[0]:
##                        count=count+1
##                    else:
##                        break
                MeasurePlotValue = Outdata[0]
                MeasurePlot.points = [(MeasurePlotValue[0] , graph2.ymin), MeasurePlotValue, (MeasurePlotValue[0], graph2.ymax)]
                #xlabel.text = str(MeasurePlotValue[0])
                ylabel.text = str(MeasurePlotValue[1])
                m,s = divmod(MeasurePlotValue[0]*60,60)
                h,m = divmod(m,60)
                xlabel.text = "%02d:%02d:%02d" % (h,m,round(s))
                return
            
        if option == 1:
            # Next Value:
            nextindex = list(DictOutdata.keys()).index(MeasurePlotValue[0])+1
            print(nextindex)
            print(len(Outdata)-1)
            if nextindex > len(Outdata)-1:
                return
            else:
                MeasurePlotValue = Outdata[nextindex]
                MeasurePlot.points = [(MeasurePlotValue[0] , graph2.ymin), MeasurePlotValue, (MeasurePlotValue[0], graph2.ymax)]
                #xlabel.text = str(MeasurePlotValue[0])
                ylabel.text = str(MeasurePlotValue[1])
                m,s = divmod(MeasurePlotValue[0]*60,60)
                h,m = divmod(m,60)
                xlabel.text = "%02d:%02d:%02d" % (h,m,round(s))
        if option == -1:
            # Next Value:
            previndex = list(DictOutdata.keys()).index(MeasurePlotValue[0])-1
            if previndex < 0:
                return
            else:
                MeasurePlotValue = Outdata[previndex]
                MeasurePlot.points = [(MeasurePlotValue[0] , graph2.ymin), MeasurePlotValue, (MeasurePlotValue[0], graph2.ymax)]
                #xlabel.text = str(MeasurePlotValue[0])
                ylabel.text = str(MeasurePlotValue[1])
                m,s = divmod(MeasurePlotValue[0]*60,60)
                h,m = divmod(m,60)
                xlabel.text = "%02d:%02d:%02d" % (h,m,round(s))




######################## REMOTE CONTROL SCREEN ###########################
class RemoteControl(Screen):    
    

    def btsend(self, bt_disp, status):
        query = "INSERT INTO flagdata(flag, timestamp) VALUES(%s, %s)"
        args = (1, datetime.datetime.now())
        cursor.execute(query, args)
        conn.commit()
        print('Successfully insert')        
        bt_disp.text = 'Successfully opened the valve!'
        status.text = 'ON'
        
            
    def btsend2(self, bt_disp, status):
        query = "INSERT INTO flagdata(flag, timestamp) VALUES(%s, %s)"
        args = (0, datetime.datetime.now())
        cursor.execute(query, args)
        conn.commit()
        print('Successfully insert')        
        bt_disp.text = 'Successfully closed the valve!'
        status.text = 'OFF'




#### Builder for Kivy ####
class MyApp(App):
    def on_pause(self):
        return True
    def build(self):
        self.root = Builder.load_file('KivyDesignFile.kv')
        return self.root

if __name__ == '__main__':
    MyApp().run()






















        
