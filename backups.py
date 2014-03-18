#!/usr/bin/env python

# Original Author: Andrew McDonald andrew@mcdee.com.au http://mcdee.com.au
# Modified by: Victor Hugo Quiroz Castro victorhqc@gmail.com http://victorhqc.com
# 
# Requires:
# https://github.com/jbardin/scp.py

# Example: mysql config file
#[client]
#host = localhost
#user = root
#password = root-pass
#
# Example: config file (JSON format)
# {
# 	"dir": "/", // Target local directory
# 	"servers": [ // Target servers so receive the backup
# 		{
# 			"dir": "/backups/", // Target remote directory
# 			"host": "server1.com", // IP address or domain
# 			"user": "root",
# 			"password": "password",
# 			"port": 22
# 		}
# 	],
# 	"emails": ["victorhqc@gmail.com"] // Emails to receive notification in case there's a problem with the backup
# }

from datetime import datetime
import sys, os, subprocess, tarfile, shutil, json, time

from paramiko import SSHClient, AutoAddPolicy
from scp import SCPClient

def print_usage(script):
	print 'Usage:', script, '--service <true|false> --mysql <mysql config file>', '--cnf <config file>'
	sys.exit(1)

def usage(args):
	default_args = {'--service': 'true', '--mysql': './mysql.cnf', '--cnf': './config.json'}
	req_args = ['--service', '--mysql', '--cnf']

	# Add default values in case they are not defined
	for a in default_args:
		if not a in args:
			args.append(a)
			args.append(default_args[a])

	if not len(args) == 7:
		print_usage(args[0])
	
	for a in req_args:
		if not a in req_args:
			print_usage()
		if a != '--service' and not os.path.exists(args[args.index(a)+1]):
			print 'Error: Path not found:', args[args.index(a)+1]
			print_usage()
	service = args[args.index('--service') + 1]
	cnf = args[args.index('--mysql') + 1]
	dir = args[args.index('--cnf') + 1]
	return service, cnf, dir

def mysql_dblist(cnf):
	no_backup = ['Database', 'information_schema', 'performance_schema', 'test']
	cmd = ['mysql', '--defaults-extra-file='+cnf, '-e', 'show databases']
	p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	stdout, stderr = p.communicate()
	if p.returncode > 0:
		print 'MySQL Error:'
		print stderr
		sys.exit(1)
	dblist = stdout.strip().split('\n')
	for item in no_backup:
		try:
			dblist.remove(item)
		except ValueError:
			continue
	if len(dblist) == 1:
		print "Doesn't appear to be any user databases found"
	return dblist

def mysql_backup(dblist, dir, cnf):
	bdate = datetime.now().strftime('%Y-%m-%d %H:%M')
	original_dir = dir
	dir += bdate
	if not os.path.exists(dir):
		os.makedirs(dir)

	for db in dblist:
		bfile =  db+'_'+bdate+'.sql'
		dumpfile = open(os.path.join(dir, bfile), 'w')
		if db == 'mysql':
			cmd = ['mysqldump', '--defaults-extra-file='+cnf, '--events', db]
		else:
			cmd = ['mysqldump', '--defaults-extra-file='+cnf,  db]
		p = subprocess.Popen(cmd, stdout=dumpfile)
		retcode = p.wait()
		dumpfile.close()
		if retcode > 0:
			print 'Error:', db, 'backup error'
		backup_compress(dir, bfile)
	return compress_dir(dir, bdate)

def backup_compress(dir, bfile):
	tar = tarfile.open(os.path.join(dir, bfile)+'.tar.gz', 'w:gz')
	tar.add(os.path.join(dir, bfile), arcname=bfile)
	tar.close()
	os.remove(os.path.join(dir, bfile))

def compress_dir(dir, bfile):
	tarf = dir + '.tar.gz'
	tar = tarfile.open(tarf, 'w')
	tar.add(dir, arcname=bfile)
	tar.close()
	shutil.rmtree(dir)

	return tarf

def backup_to_server(servers, tarfile):
	ssh = SSHClient()
	ssh.load_system_host_keys()
	ssh.set_missing_host_key_policy(AutoAddPolicy())
	for server in servers:
		ssh.connect(server['host'], port=server['port'], username=server['user'], password=server['password'])

		# SCPCLient takes a paramiko transport as its only argument
		scp = SCPClient(ssh.get_transport())
		scp.put(tarfile, server['dir'])


def read_config_file(cnf):
	f = open(cnf, 'r')
	string = f.read()
	js = json.loads(string)
	return js

def tasks(mysql, cnf):
	js = read_config_file(cnf)
	dblist = mysql_dblist(mysql)
	f = mysql_backup(dblist, js['dir'], mysql)
	backup_to_server(js['servers'], f)

def main():
	service, mysql, cnf = usage(sys.argv)

	if(service == True or service == 'true' or service == 'True'):
		delay_time = 60 * 60 * 24 # Time in seconds (24 hour delay)
		# Infinite loop
		while True:
			tasks(mysql, cnf)
			time.sleep(delay_time)
	else:
		tasks(mysql, cnf)

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print >> sys.stderr, '\nExiting by user request.\n'
        sys.exit(0)