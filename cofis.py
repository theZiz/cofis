#!/usr/bin/python
# ---------------------------------------------------------------------
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See
# the License for the specific language governing rights and limitations
# under the License.
#                                                         
# Alternatively, the contents of this file may be used under the terms
# of the GNU Lesser General Public license (the  "LGPL License"), in
# which case the provisions of LGPL License are applicable instead of
# those above.
#                                                               
# For feedback and questions about my Files and Projects please mail me,
# Alexander Matthes (Ziz) , zizsdl_at_googlemail.com
# ---------------------------------------------------------------------

import stat
import errno
import fuse
import time
import subprocess
import hashlib

NODE_COUNT   = 5
NODE_PRAEFIX = 'riddick'
cpuCount = 2
sdaCount = 1


fuse.fuse_python_api = (0, 2)

class DefaultOutput():
    def __init__(self):
        self.refresh()
            
    def refresh(self):
        self.output = "default output"
        self.output = self.output+'\n'
        
    def getOutput(self):
        self.refresh()
        return self.output
        
    def getOutputLength(self):
        self.refresh()
        return len(self.output)
        
class TempOutput(DefaultOutput):
    def __init__(self,node_,cpu_):
        self.node=node_
        self.cpu=cpu_
    
    def refresh(self):
        if self.node == 0:
            process = subprocess.Popen('sensors | grep "Core '+str(self.cpu)+'"',stdout=subprocess.PIPE,shell=True)
        else:
            process = subprocess.Popen('ssh '+NODE_PRAEFIX+str(self.node)+' sensors | grep "Core '+str(self.cpu)+'"',stdout=subprocess.PIPE,shell=True)
        output = process.stdout.read().split('\n')
        output = output[0].split(' ')
        while '' in output:
            output.remove('')
        self.output = output[2]
        self.output = self.output+'\n'

class UsersOutput(DefaultOutput):
    def __init__(self,node_):
        self.node = node_
    
    def refresh(self):
        if self.node == 0:
            process = subprocess.Popen('users',stdout=subprocess.PIPE,shell=True)
        else:
            process = subprocess.Popen('ssh '+NODE_PRAEFIX+str(self.node)+' users',stdout=subprocess.PIPE,shell=True)
        output = process.stdout.read().split('\n')
        output = output[0].split(' ')
        while '' in output:
            output.remove('')
        self.output = ""
        was_named = []
        for user in output:
            if user not in was_named:
                self.output += user + '\n'
                was_named.extend([user])

class FSOutput(DefaultOutput):
    def __init__(self,node_,sda_):
        self.node = node_
        self.sda = sda_
    
    def refresh(self):
        if self.node == 0:
            process = subprocess.Popen('df -h | grep "sda'+str(self.sda)+'"',stdout=subprocess.PIPE,shell=True)
        else:
            process = subprocess.Popen('ssh '+NODE_PRAEFIX+str(self.node)+' df -h | grep "sda'+str(self.sda)+'"',stdout=subprocess.PIPE,shell=True)
        output = process.stdout.read().split('\n')
        output = output[0].split(' ')
        while '' in output:
            output.remove('')
        self.output  = "      Size: " + output[1] + '\n'
        self.output += "      Used: " + output[2] + '\n'
        self.output += "   Avaible: " + output[3] + '\n'
        self.output += "Use (in %): " + output[4] + '\n'
        self.output += "Mounted on: " + output[5] + '\n'

class NetOutput(DefaultOutput):
    def __init__(self,node_,net_):
        self.node = node_
        self.net = net_
    
    @staticmethod
    def getNetworkAdapters(node):
        if node == 0:
            process = subprocess.Popen('ifconfig -a',stdout=subprocess.PIPE,shell=True)
        else:
            process = subprocess.Popen('ssh '+NODE_PRAEFIX+str(node)+' ifconfig -a',stdout=subprocess.PIPE,shell=True)
        rawoutput = process.stdout.read().split('\n')
        output = []
        for line in rawoutput:
            if not line.startswith(' '):
                output.extend([line])
        result = []
        for line in output:
            result.extend([line.split(' ')[0]])
        while '' in result:
            result.remove('')
        return result
    
    def refresh(self):
        if self.node == 0:
            process = subprocess.Popen('ifconfig '+str(self.net),stdout=subprocess.PIPE,shell=True)
        else:
            process = subprocess.Popen('ssh '+NODE_PRAEFIX+str(self.node)+' ifconfig '+str(self.net),stdout=subprocess.PIPE,shell=True)
        rawoutput = process.stdout.read().split('\n')
        output = []
        for line in rawoutput:
            output.extend([line.split('  ')])
        for line in output:
            while '' in line:
                line.remove('')
        del output[0][0]
        self.output = ""
        for line in output:
            for sign in line:
                self.output += sign + '\n'

class MemTotalOutput(DefaultOutput):
    def __init__(self,node_):
        self.node = node_
    
    def refresh(self):
        if self.node == 0:
            process = subprocess.Popen('free -m',stdout=subprocess.PIPE,shell=True)
        else:
            process = subprocess.Popen('ssh '+NODE_PRAEFIX+str(self.node)+' free -m',stdout=subprocess.PIPE,shell=True)
        rawoutput = process.stdout.read().split('\n')
        output = []
        for line in rawoutput:
            output.extend([line.split(' ')])
        for line in output:
            while '' in line:
                line.remove('')
        self.output  = 'Avaible: ' + output[1][1] + ' MB' + '\n'
        self.output += '   Used: ' + output[1][2] + ' MB (with cache)' + '\n'
        self.output += '         ' + output[2][2] + ' MB (real)' + '\n'
        self.output += '   Free: ' + output[1][3] + ' MB (with cache)' + '\n'
        self.output += '         ' + output[2][3] + ' MB (real)' + '\n'
        self.output += ' Shared: ' + output[1][4] + ' MB' + '\n'
        self.output += 'Buffers: ' + output[1][5] + ' MB' + '\n'
        self.output += ' Cached: ' + output[1][6] + ' MB' + '\n'
        self.output += 'SWAP Avaible: ' + output[3][1] + ' MB' + '\n'
        self.output += '        Used: ' + output[3][2] + ' MB' + '\n'
        self.output += '        Free: ' + output[3][3] + ' MB' + '\n'

class MemTopOutput(DefaultOutput):
    def __init__(self,node_,maxvalues_):
        self.node = node_
        self.maxvalues = maxvalues_
    
    def refresh(self):
        if self.node == 0:
            process = subprocess.Popen('ps axo rss,vsz,comm,pid,user,tty',stdout=subprocess.PIPE,shell=True)
        else:
            process = subprocess.Popen('ssh '+NODE_PRAEFIX+str(self.node)+' ps axo rss,vsz,comm,pid,user,tty',stdout=subprocess.PIPE,shell=True)
        output = process.stdout.read().split('\n')[1:]
        output = output[:len(output)-1]
        rawoutput = []
        for line in output:
            rawoutput.extend([line.split(' ')])
        for line in rawoutput:
            while '' in line:
                line.remove('')
        
        #Sortieren:
        minrange = min(len(output),self.maxvalues)
        for i in range(minrange):
            for j in range(i,len(output)):
                if int(rawoutput[i][0])<int(rawoutput[j][0]):
                    temp = rawoutput[i][0]
                    rawoutput[i][0] = rawoutput[j][0]
                    rawoutput[j][0] = temp
                    temp = output[i]
                    output[i] = output[j]
                    output[j] = temp
        
        self.output = ""
        for i in range(self.maxvalues):
            if i < len(output):
                self.output += output[i] + '\n'

class CpuTotalOutput(DefaultOutput):
    def __init__(self,node_):
        self.node = node_
    
    def refresh(self):
        if self.node == 0:
            process = subprocess.Popen('cat /proc/stat',stdout=subprocess.PIPE,shell=True)
        else:
            process = subprocess.Popen('ssh '+NODE_PRAEFIX+str(self.node)+' cat /proc/stat',stdout=subprocess.PIPE,shell=True)
        rawoutput = process.stdout.read().split('\n')
        output = []
        for line in rawoutput:
            output.extend([line.split(' ')])
        for line in output:
            while '' in line:
                line.remove('')
        cpucount = 0
        for line in output:
            if (len(line)>0) and (line[0].startswith('cpu')):
                cpucount += 1
        
        sum = float(output[0][1]) + float(output[0][2]) + float(output[0][3]) + float(output[0][4])
        self.output  = 'All CPU:' + '\n'
        self.output += '   User: ' + ('%.2f' % (float(output[0][1])*100.0/sum,)).rstrip('0').rstrip('.') + ' %' + '\n'
        self.output += '   Nice: ' + ('%.2f' % (float(output[0][2])*100.0/sum,)).rstrip('0').rstrip('.') + ' %' + '\n'
        self.output += ' System: ' + ('%.2f' % (float(output[0][3])*100.0/sum,)).rstrip('0').rstrip('.') + ' %' + '\n'
        self.output += '    Sum: ' + ('%.2f' % ((float(output[0][1])+float(output[0][2])+float(output[0][3]))*100.0/sum,)).rstrip('0').rstrip('.') + ' %' + '\n'
        self.output += '   Idle: ' + ('%.2f' % (float(output[0][4])*100.0/sum,)).rstrip('0').rstrip('.') + ' %' + '\n'
        for i in range(1,cpucount):
            sum = float(output[i][1]) + float(output[i][2]) + float(output[i][3]) + float(output[i][4])
            self.output += 'CPU' + str(i) + ':' + '\n'
            self.output += '   User: ' + ('%.2f' % (float(output[i][1])*100.0/sum,)).rstrip('0').rstrip('.') + ' %' + '\n'
            self.output += '   Nice: ' + ('%.2f' % (float(output[i][2])*100.0/sum,)).rstrip('0').rstrip('.') + ' %' + '\n'
            self.output += ' System: ' + ('%.2f' % (float(output[i][3])*100.0/sum,)).rstrip('0').rstrip('.') + ' %' + '\n'
            self.output += '    Sum: ' + ('%.2f' % ((float(output[i][1])+float(output[i][2])+float(output[i][3]))*100.0/sum,)).rstrip('0').rstrip('.') + ' %' + '\n'
            self.output += '   Idle: ' + ('%.2f' % (float(output[i][4])*100.0/sum,)).rstrip('0').rstrip('.') + ' %' + '\n'

class CpuTopOutput(DefaultOutput):
    def __init__(self,node_,maxvalues_):
        self.node = node_
        self.maxvalues = maxvalues_
    
    def refresh(self):
        if self.node == 0:
            process = subprocess.Popen('ps axo pcpu,comm,pid,user,tty',stdout=subprocess.PIPE,shell=True)
        else:
            process = subprocess.Popen('ssh '+NODE_PRAEFIX+str(self.node)+' ps axo pcpu,comm,pid,user,tty',stdout=subprocess.PIPE,shell=True)
        output = process.stdout.read().split('\n')[1:]
        output = output[:len(output)-1]
        rawoutput = []
        for line in output:
            rawoutput.extend([line.split(' ')])
        for line in rawoutput:
            while '' in line:
                line.remove('')
        
        #Sortieren:
        minrange = min(len(output),self.maxvalues)
        for i in range(minrange):
            for j in range(i,len(output)):
                if float(rawoutput[i][0])<float(rawoutput[j][0]):
                    temp = rawoutput[i][0]
                    rawoutput[i][0] = rawoutput[j][0]
                    rawoutput[j][0] = temp
                    temp = output[i]
                    output[i] = output[j]
                    output[j] = temp
        
        self.output = ""
        for i in range(self.maxvalues):
            if i < len(output):
                self.output += output[i] + '\n'


class DefaultStat(fuse.Stat):
    def __init__(self):
        self.st_mode = stat.S_IFDIR | 0755
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 2
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0 # 4096
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0

def getDataDir(nodeNumber):
    data = []
    #if nodeNumber == 0:
    #    data.extend(['jobs'])
    data.extend(['cpu','mem','temp','fs','net','users'])
    return data

def getDataFiles(nodeNumber,folder):
    data = []
    if folder == 'temp':
        for i in range(cpuCount):
            data.extend(['cpu'+str(i)])
    elif folder == 'fs':
        for i in range(sdaCount):
            data.extend(['sda'+str(i+1)])
    elif folder == 'net':
        data.extend(NetOutput.getNetworkAdapters(nodeNumber))
    elif (folder == 'mem') or (folder == 'cpu'):
        data.extend(['total','top10','top20','all'])
    return data

class MyFS(fuse.Fuse):    
    def __init__(self, *args, **kw):
        fuse.Fuse.__init__(self, *args, **kw)
        #Ordner nach Anzahl der Nodes bestimmen
        self.nodes = []
        for i in range(NODE_COUNT):
            self.nodes.extend([NODE_PRAEFIX+str(i)])
        #self.jobOutput = DefaultOutput()
        self.tempOutput = []
        self.usersOutput = []
        self.fsOutput = []
        self.netOutput = []
        self.memTotalOutput = []
        self.memTopOutput = []
        self.cpuTotalOutput = []
        self.cpuTopOutput = []
        for node in range(NODE_COUNT):
            self.tempOutput.extend([[]])
            for cpu in range(cpuCount):
                self.tempOutput[node].extend([TempOutput(node,cpu)])
            self.usersOutput.extend([UsersOutput(node)])
            self.fsOutput.extend([[]])
            for sda in range(sdaCount):
                self.fsOutput[node].extend([FSOutput(node,sda+1)])
            self.netOutput.extend([{}])
            for adapter in NetOutput.getNetworkAdapters(node):
                self.netOutput[node][adapter] = NetOutput(node,adapter)
            self.memTotalOutput.extend([MemTotalOutput(node)])
            self.memTopOutput.extend([{'top10':MemTopOutput(node,10),'top20':MemTopOutput(node,20),'all':MemTopOutput(node,65535)}])
            self.cpuTotalOutput.extend([CpuTotalOutput(node)])
            self.cpuTopOutput.extend([{'top10':CpuTopOutput(node,10),'top20':CpuTopOutput(node,20),'all':CpuTopOutput(node,65535)}])
            
    def getattr(self, path):  #path: 0 riddickX, 1 task, 2 files
        st = DefaultStat()
        pe = path[1:].split('/')
        #if path == '/'+NODE_PRAEFIX+'0/jobs':
        #    st.st_mode = stat.S_IFREG | 0444
        #    st.st_nlink = 1
        #    st.st_size = self.jobOutput.getOutputLength()
        if (len(pe) == 2) and (pe[1] == 'users'):
            st.st_mode = stat.S_IFREG | 0444
            st.st_nlink = 1
            st.st_size = 0
            nodenumber = int(pe[0][len(NODE_PRAEFIX):])
            st.st_size = self.usersOutput[nodenumber].getOutputLength()
        elif len(pe) == 3:
            st.st_mode = stat.S_IFREG | 0444
            st.st_nlink = 1
            st.st_size = 0
            nodenumber = int(pe[0][len(NODE_PRAEFIX):])
            if pe[1] == 'temp':
                cpu = int(pe[2][3:])
                st.st_size = self.tempOutput[nodenumber][cpu].getOutputLength()
            elif pe[1] == 'fs':
                sda = int(pe[2][3:])
                st.st_size = self.fsOutput[nodenumber][sda-1].getOutputLength()
            elif pe[1] == 'net':
                adapter = pe[2]
                st.st_size = self.netOutput[nodenumber][adapter].getOutputLength()
            elif pe[1] == 'mem':
                if pe[2] == 'total':
                    st.st_size = self.memTotalOutput[nodenumber].getOutputLength()
                else:
                    st.st_size = self.memTopOutput[nodenumber][pe[2]].getOutputLength()
            elif pe[1] == 'cpu':
                if pe[2] == 'total':
                    st.st_size = self.cpuTotalOutput[nodenumber].getOutputLength()
                else:
                    st.st_size = self.cpuTopOutput[nodenumber][pe[2]].getOutputLength()
        return st
        
    def readdir(self, path, offset):
        dirents = [ '.', '..' ]
        pe = path.split('/')[1:]
        if path == '/':
            dirents.extend(self.nodes)
        else:
            nodenumber = int(pe[0][len(NODE_PRAEFIX):])
            if path[1:].startswith(NODE_PRAEFIX) and (len(pe)==1):
                dirents.extend(getDataDir(nodenumber))
            elif path[1:].startswith(NODE_PRAEFIX) and (len(pe)==2):
                dirents.extend(getDataFiles(nodenumber,pe[1]))
        for r in dirents:
            yield fuse.Direntry(r)

    def mknod(self, path, mode, dev):
        return 0

    def unlink(self, path):
        return 0

    def read(self, path, size, offset):
        pe = path.split('/')[1:]
        #if path == '/riddick0/jobs':
        #    return self.jobOutput.getOutput()[offset:offset+size]
        if (len(pe) == 2) and (pe[1] == 'users'):
            nodenumber = int(pe[0][len(NODE_PRAEFIX):])
            return self.usersOutput[nodenumber].getOutput()[offset:offset+size]
        elif len(pe) == 3:
            nodenumber = int(pe[0][len(NODE_PRAEFIX):])
            if pe[1] == 'temp':
                cpu = int(pe[2][3:])
                return self.tempOutput[nodenumber][cpu].getOutput()[offset:offset+size]
            elif pe[1] == 'fs':
                sda = int(pe[2][3:])
                return self.fsOutput[nodenumber][sda-1].getOutput()[offset:offset+size]
            elif pe[1] == 'net':
                adapter = pe[2]
                return self.netOutput[nodenumber][adapter].getOutput()[offset:offset+size]
            elif pe[1] == 'mem':
                if pe[2] == 'total':
                    return self.memTotalOutput[nodenumber].getOutput()[offset:offset+size]
                else:
                    return self.memTopOutput[nodenumber][pe[2]].getOutput()[offset:offset+size]
            elif pe[1] == 'cpu':
                if pe[2] == 'total':
                    return self.cpuTotalOutput[nodenumber].getOutput()[offset:offset+size]
                else:
                    return self.cpuTopOutput[nodenumber][pe[2]].getOutput()[offset:offset+size]
        return 0

    def write(self, path, buf, offset):
        return len(buf)

    def release(self, path, flags):
        return 0

    def open(self, path, flags):
        return 0

    def truncate(self, path, size):
        return 0

    def utime(self, path, times):
        return 0

    def mkdir(self, path, mode):
        return 0

    def rmdir(self, path):
        return 0

    def rename(self, pathfrom, pathto):
        return 0

    def fsync(self, path, isfsyncfile):
        return 0

def main():
    fs = MyFS(version="%prog " + fuse.__version__,usage=fuse.Fuse.fusage, dash_s_do='setsingle')
    fs.parse(errex=1)
    fs.main()

if __name__ == '__main__':
    main()

