#!/usr/bin/env python

todo="""make scan_dir a local variable that is passed around"""
usage="""Usage for unrar.py: python unrar.py -s "directory" [--other-options]
Will unpack rars recursively in scanned directory outputing them based on provided options (default --same-dir)
	-s/--scan-dir <directory> (Required): set scan directory
	-v/--verbose: Will not be noisy by default. Provide this option to get lots of messages about the operations.
	-d/--delete: Will delete successfully extracted archives. will delete associated .sfv files, if any. will also delete empty directories. Search source for 'sample' to see example code on how to delete sample directories (potentially unsafe, however)
	-t/--target-dir <directory>: Will extract the files to the directory specified here
	-p/--parent-dir: if rar is a file immediately below scan-dir, will extract to scan-dir. If in a folder in scan-dir, will extract to that folder, even if it is in a subfolder of that folder
	-S/--same-dir: will extract to the same directory that the rar is held in (Default behavior)
	-h/--help: this message"""
__copyright__ = "GPL v2"
__author__ = "lostnihilst@gmail.com"
__contributor__ = u"""This code is largely based on unpack.py found at the following link, with significant changes to functionality and code cleanup. RAR_RE would probably not have been possible without it: https://svn.madcowdisease.org/mcd/misc/trunk/unpack.py"""

import getopt, os, re, shutil, sys, time, sha, pickle, gzip

__copyright__ = "GPL"
__version__ = '0.5.0'
RAR_RE = re.compile(r'^(.*?)(?:\.part\d+|)\.(?:rar|r\d\d|\d\d\d)$', re.I) #hopefully this works consistently, someone else created this
scan_dirs = scan_dir = target_d = verbose = delete = action = None
sfv = True
sample = False

def getRarPath():
	RAR_COMMAND = None
	if not RAR_COMMAND:
		if os.name == 'nt': 
			lookhere = os.getenv('PATH').split(';')
			findrar = ('rar.exe', 'unrar.exe')
		else: 
			lookhere = os.getenv('PATH').split(':')
			findrar = ('rar', 'unrar', 'rar3', 'unrar3', )
		for path in lookhere:
			if not RAR_COMMAND:
				for rar in findrar:
					rar_path = os.path.join(path, rar)
					if os.path.isfile(rar_path) and os.access(rar_path, os.X_OK):
						RAR_COMMAND = rar_path
						break
	if RAR_COMMAND is None:		Error("couldn't find your rar/unrar binary!")
	elif verbose: print "found rar binary"
	return RAR_COMMAND

def Error(text, exit=1):
	sys.stderr.write( 'ERROR: %s%s' % ( text, os.linesep ) )
	if exit: raise SystemExit, 1

def getFileList(scan_dir):
	if verbose: print "getting file list"
	files = []
	for (dirname, dirshere, fileshere) in os.walk(scan_dir):
		for filename in fileshere:
			if RAR_RE.match(filename): files.append( os.path.join(dirname, filename) )
	files.sort() # maybe necessary due to os.walk, but maybe not..
	return files

def getExtractDir(key, scan_dir):
	if verbose: print "discovering where to extract"
	extractDir = None
	if action == 'parent-dir':
		extractDir, subdir = os.path.split(key)
		while extractDir != scan_dir:
			extractDir, subdir = os.path.split(extractDir)
		else: extractDir = os.path.join(extractDir, subdir)
		if not os.path.isdir(extractDir): extractDir = os.path.split(extractDir)[0]
	elif action == 'same-dir':
		extractDir = os.path.split(key)[0]
	elif action == 'target-dir':
		extractDir = target_d
	if not os.path.isdir(extractDir): Error('for the love of god, where is the extraction directory!')
	if verbose: "found extraction directory %s for %s" % (extractDir, key)
	return extractDir
	
def RAR_Check(path, files):
	global RAR_COMMAND
	# Find the RAR files
	bases = {}
	totalbytes = totalfiles = 0
	for filename in files:
		m = RAR_RE.match(filename)
		if m:
			bases.setdefault(m.group(1), []).append(filename)
			if verbose: print "found rar %s" % filename
			file_path = os.path.join(path, filename)
			totalbytes += os.path.getsize(file_path)
			totalfiles += 1
	for key in bases.keys():
		if rarExists( getExtractDir(key, scan_dir), bases[key][0] ): del bases[key] # don't extract existing files
	return bases, (totalbytes, totalfiles)

def rarExists(extractDir, rarname):
	global RAR_COMMAND
	stin, stout, sterr = os.popen3('%s v %s' % (RAR_COMMAND, rarname) )
	stin.close()
##	if sterr.read(): 
##		Error ('error reading archive', exit=0)
##		return True # not really, but might as well not try extracting archives whose names cannot be read
	for i in stout.xreadlines():
		if re.match(' \S', i):
			if os.path.exists( os.path.join(extractDir, i.strip()) ): return True  # file already exists
	return False

def extractFiles(extractDir, base, rars, totalbytes, totalfiles):
	"a bit unwieldy, could try cutting this down some, and splitting up"
	global delete
	pre = '=>'
	if verbose: print '%s Found %d archives (%.1fMB)' % (pre, totalfiles, totalbytes / 1024.0 / 1024.0)
	numrars = len(rars)
	rarpresent = rarExists(extractDir, rars[0])
	if rarpresent == None or rarpresent == True: return None
	command = '%s x -idp -o+ "%s" "%s"' % (RAR_COMMAND, rars[0], extractDir)
	stin, proc = os.popen4(command, 't')
	stin.close()
	if verbose: print "\r%s Unpacking '%s' : 00/%02d" % (pre, base, numrars)
	start = time.time()
	extracted = runRar(proc, base, numrars, pre)
	if extracted == False: return None # unrar failed, restart loop in main
	elapsed = time.time() - start
	hours, elapsed = divmod(elapsed, 60*60)
	mins, secs = divmod(elapsed, 60)
	if hours:			elapsed = '%d:%02d:%02d' % (hours, mins, secs)
	else:			elapsed = '%d:%02d' % (mins, secs)
	if verbose: print "\r%s Unpacked '%s' %d file(s) in %s	" % (pre, base, len(extracted), elapsed)
	if delete == True:		deleteFiles(rars, base)
	bases, rarFileData = RAR_Check( extractDir, extracted ) # if flat versus directory, may not find...? if we are not deleting, and looking in same directory, do we keep finding rars?
	if bases:		searchRarsAndRun( scan_dir, bases, rarFileData )

def deleteFiles( rars, base, ):
	for rar in rars: 
		os.unlink(rar)
		if verbose: print 'deleting %s' % rar
	global sfv, sample
	if sfv and os.path.isfile( base+'.sfv'): 
		os.unlink( base+'.sfv' ) 
		if verbose: print 'deleting %s.sfv' % base
	if sample:
		sampleList = filter( lambda x: x.lower() == 'sample', os.listdir( os.path.dirname(base) ) )
		for i in sampleList:
			try: shutil.rmtree(i)
			except: Error('could not remove sample directory %s' % i, exit=0)
	if not os.listdir( os.path.dirname(base) ): os.rmdir( os.path.dirname(base) ) # if this doesn't go from deepest do shallowest, this will not works :(


def searchRarsAndRun( scan_dir, bases, rarFileData):
	keys = bases.keys()
	keys.sort()
	keys.reverse() #hopefully go from deepest to less deep
	for key in keys:		extractFiles(getExtractDir(key, scan_dir), key, bases[key], *rarFileData)
	
def runRar(proc, base, numrars, pre):
	curr = 0
	extracted = []
	for line in proc.xreadlines():
		line = line.strip()
		if line.startswith('Extracting from'):
			curr += 1
			if verbose: print "\r%s Unpacking '%s' : %02d/%02d" % (pre, base, curr, numrars),
		elif line.startswith('Cannot find volume'):
			filename = os.path.basename(line[19:])
			Error("'%s' is missing!" % filename, exit=0)
			return False
		elif line.endswith('CRC failed'):				
			Error('CRC failure! on somewhere in %s' % base, exit=0)
			return False
		elif line.startswith('Write error'):
			for filename in extracted:	os.remove(filename)
			Error('Write error, disk full?!', exit=0)
			return False
		else:
			m = re.match(r'^(Extracting|...)\s+(.*?)\s+OK\s*$', line)
			if m:		extracted.append(m.group(2))
	return extracted
	
def main():
	global scan_dir, scan_dirs, infoStoreFilename
	for scan_dir in scan_dirs:
		files = getFileList(scan_dir)
		bases, rarFileData = RAR_Check( scan_dir, files )
		if bases:		searchRarsAndRun( scan_dir, bases, rarFileData )

def processArgs(scan_dirs , target_d , verbose , delete , action ):
	action = 'same-dir'
	try:		opts, args = getopt.getopt(sys.argv[1:], "dhs:t:vpS", ['delete', "help", "scan-dir=", "target-dir=", "verbose", "parent-dir", "same-dir", ])
	except getopt.GetoptError: raise SystemExit, 1
	scan_dirs = []
	for param , opt in opts:
		if    param == "-h" or param == "--help": 
			print usage
			raise SystemExit
		elif param == "-s" or param == "--scan-dir": 
			scan_dirs.append( os.path.abspath(opt) )
			if not os.path.isdir(scan_dirs[-1]):		Error('directory %s does not exist, or is not a directory!' % scan_dir)
		elif param == "-t" or param == "--target-dir": 
			target_d = os.path.abspath(opt)
			if not os.path.isdir(target_d): Error('directory %s does not exist, or is not a directory!' % target_d)
			action = 'target-dir'
		elif param == "-v" or param == "--verbose": verbose = True
		elif param == "-S" or param == "--same-dir": action = 'same-dir'
		elif param == "-p" or param == "--parent-dir": action = 'parent-dir'
		elif param == "-d" or param == "--delete": delete = True
		else:	Error("unknown parameter %s, exiting" % param )
		if scan_dirs == []: 
			print usage
			raise SystemExit
	return scan_dirs , target_d , verbose , delete , action

if __name__ == '__main__' and len(sys.argv) > 1:
	RAR_COMMAND = getRarPath()
	scan_dirs , target_d , verbose , delete , action = processArgs(scan_dirs , target_d , verbose , delete , action)
	if verbose: print '* Scanning directory: %s' % (scan_dir)
	main()
elif __name__ == '__main__': print usage

