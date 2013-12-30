#!/bin/env python                                                                                                                                                      
'''                                                                                                                                                                    
Created on 2012-3-20                                                                                                                                                   
                                                                                                                                                                         
@author: Administrator                                                                                                                                                 
'''
import sys, os
import threading
import subprocess
import time
  
class Deploy():
    (COMMAND_LUNCH_SCRIPT, COMMAND_LUNCH_SCRIPT_WITH_TTY, COMMAND_COPY_TO, COMMAND_COPY_FROM) = range(4)
    def __init__(self, args):
        self.user = 'operation'
        self.method = None
        self.hosts = []
        self.rename = False
        self.remote = None
        self.local = []
        self.cmd = None
        self.sysargs = args
        pass
  
    def usage(self):
        """                                                                                                                                                            
        deploy script usage                                                                                                                                            
        """
        program = self.sysargs[0]
        print('usage:')
        print('    %s [-u username] <host_file|host_list> -l \"cd /data && ls\"' % (program,))
        print('        excute script on remote hosts')
        print('    %s [-u username] <host_file|host_list> -L \"cd /data && ls\"' % (program,))
        print('        excute script with tty on remote hosts')
        print('    %s [-u username] <host_file|host_list> localpath :remotepath' % (program,))
        print('        copy files to remote hosts')
        print('    %s [-u username] <host_file|host_list> [-n] :remotepath localpath' % (program,))
        print('        copy files from remote hosts')
        print('    host_file:= -f /path/to/hostfile')
        print('    host_list:= -s \"10.7.18.147 10.7.18.148\"')
        print('    -n option: auto rename')
        sys.exit(0)
  
    def parse_options(self):
        args = self.sysargs[1:]
        # parse user if specified
        if len(args) >= 2 and args[0] == '-u':
            self.user = args[1]
            args = args[2:]
        # parse hosts
        hosts = []
        if len(args) >= 2 and args[0] == '-f':
            hosts = open(args[1], "r").readlines()
        elif len(args) >= 2 and args[0] == '-s':
            hosts = args[1].split()
        else:
            self.usage()
        self.hosts = [host.strip() for host in hosts]
  
        args = args[2:]
        if len(args) < 2:
            self.usage()
        if args[0] == '-l':
            self.cmd = args[1]
            self.method = Deploy.COMMAND_LUNCH_SCRIPT
            return
        elif args[0] == '-L':
            self.cmd = args[1]
            self.method = Deploy.COMMAND_LUNCH_SCRIPT_WITH_TTY
            return
        elif args[0] == '-n':
            self.rename = True
            args = args[1:]
  
        if len(args) < 2:
            self.usage()
        if args[0].startswith(':'):
            self.method = Deploy.COMMAND_COPY_FROM
            self.remote = args[0][1:]
            self.local.append(args[1])
        else:
            self.method = Deploy.COMMAND_COPY_TO
            if not args[-1].startswith(":"):
                self.usage()
            self.remote = args[-1][1:]
            self.local = args[:-1]
    def confirm(self):
        pass
    def start(self):
        self.parse_options()
        self.confirm()
        threads = []
        max_active_thread = 20
        if self.method == Deploy.COMMAND_LUNCH_SCRIPT:
            max_active_thread = 100
        elif self.method == Deploy.COMMAND_LUNCH_SCRIPT_WITH_TTY:
            max_active_thread = 1
            pass
        for host in self.hosts:
            print(host)
            if self.method == Deploy.COMMAND_COPY_FROM:
                t = _CopyFrom(self.user, host, self.remote, self.local[0], self.rename)
            elif self.method == Deploy.COMMAND_COPY_TO:
                t = _CopyTo(self.user, host, self.remote, self.local)
            elif self.method == Deploy.COMMAND_LUNCH_SCRIPT:
                t = _ExcuteCmd(self.user, host, self.cmd, False)
            elif self.method == Deploy.COMMAND_LUNCH_SCRIPT_WITH_TTY:
                t = _ExcuteCmd(self.user, host, self.cmd, True)
            while threading.active_count() > max_active_thread:
                #print("wait active thread to drop below %d" % (max_active_thread,))
                time.sleep(1)
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
  
  
def remote_excute(user, host, cmd, with_tty):
    if with_tty:
        fullcmd = "ssh -t -o \"StrictHostKeyChecking no\" " + user + "@" + host + " \"" + cmd + "\""
    else:
        fullcmd = "ssh -o \"StrictHostKeyChecking no\" " + user + "@" + host + " \"" + cmd + "\""
    print(fullcmd)
    return subprocess.call(fullcmd, shell = True)

def remote_excute_getoutput(user, host, cmd):
    fullcmd = "ssh -T -o \"StrictHostKeyChecking no\" " + user + "@" + host + " \"" + cmd + "\""
    print(fullcmd)
    output = subprocess.Popen(fullcmd, stdout=subprocess.PIPE, shell=True).communicate()[0] 
    return output
  
class _CopyFrom(threading.Thread):
    """                                                                                                                                                                
    copy files from host to local                                                                                                                                      
    """
    def __init__(self, user, host, remote, local, rename):
        threading.Thread.__init__(self)
        self.user = user
        self.host = host
        self.remote = remote
        self.local = local
        self.rename = rename
    def run(self):
        if not self.rename:
            cmd = "scp -r " + self.user + "@" + self.host + ":" + self.remote + " " + self.local
            print(cmd)
            os.system(cmd)
        else:
            basename = os.path.basename(self.remote)
            dirname = os.path.dirname(self.remote)
            remote_cmd = "cd " + dirname + " && ls ./" + basename
            filenames = remote_excute_getoutput(self.user, self.host, remote_cmd).split()
            for filename in filenames:
                path = os.path.normpath(os.path.join(dirname, filename))
                filerenamed = filename + "." + self.host
                cmd = "scp -r " + self.user + "@" + self.host + ":" + path + " " + os.path.normpath(os.path.join(self.local, filerenamed))
                print(cmd)
                os.system(cmd);
  
  
class _CopyTo(threading.Thread):
    """                                                                                                                                                                
    copy files from local to remote                                                                                                                                    
    """
    def __init__(self, user, host, remote, local):
        threading.Thread.__init__(self)
        self.user = user
        self.host = host
        self.remote = remote
        self.local = local
    def run(self):
        cmd = "scp -r " + " ".join(self.local) + " " + self.user + "@" + self.host + ":" + self.remote
        print(cmd)
        os.system(cmd);
  
class _ExcuteCmd(threading.Thread):
    def __init__(self, user, host, cmd, with_tty):
        threading.Thread.__init__(self)
        self.user = user
        self.host = host
        self.cmd = cmd
        self.with_tty = with_tty
    def run(self):
        output = remote_excute(self.user, self.host, self.cmd, self.with_tty)
        print(output)
  
def check_python_version():
    version_required = (3, 0)
    version = sys.version_info[:2]
    if version < version_required:
        print("python 3.0 or later is required to run this script")
        sys.exit(0)
  
if __name__ == '__main__':
    #check_python_version()
    dep = Deploy(sys.argv)
    dep.start()
    pass
