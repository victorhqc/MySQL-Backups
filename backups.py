#!/usr/bin/python

# Original Author: Andrew McDonald andrew@mcdee.com.au http://mcdee.com.au
# Modified by: Victor Hugo Quiroz Castro victorhqc@gmail.com http://victorhqc.com
# 
# Requires:
# https://github.com/jbardin/scp.py

# Example: config file
#[client]
#host = localhost
#user = root
#password = root-pass

from datetime import datetime
import sys, os, subprocess, tarfile, shutil

from paramiko import SSHClient
from scp import SCPClient

def print_usage(script):
	print 'Usage:', script, '--cnf <config file>', '--todir <directory>'
	sys.exit(1)

def usage(args):
	if not len(args) == 5:
		print_usage(args[0])
	else:
		req_args = ['--cnf', '--todir']
		for a in req_args:
			if not a in req_args:
				print_usage()
			if not os.path.exists(args[args.index(a)+1]):
				print 'Error: Path not found:', args[args.index(a)+1]
				print_usage()
	cnf = args[args.index('--cnf')+1]
	dir = args[args.index('--todir')+1]
	return cnf, dir

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
	return compress_dir(original_dir, bdate)

def backup_compress(dir, bfile):
	tar = tarfile.open(os.path.join(dir, bfile)+'.tar.gz', 'w:gz')
	tar.add(os.path.join(dir, bfile), arcname=bfile)
	tar.close()
	os.remove(os.path.join(dir, bfile))

def compress_dir(dir, bfile):
	tarf = os.path.join(dir, bfile) + '.tar.gz'
	tar = tarfile.open(tarf, 'w')
	tar.add(dir, arcname=bfile)
	tar.close()
	shutil.rmtree(os.path.join(dir, bfile))

	return tarf

def backup_to_server(file):
	

def main():
	cnf, dir = usage(sys.argv)
	dblist = mysql_dblist(cnf)
	file = mysql_backup(dblist, dir, cnf)
	backup_to_server(file)

if __name__ == '__main__':
	main()