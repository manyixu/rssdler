def ifTorrent(directory, filename, rssItemNode, retrievedLink, downloadDict, threadName):
	global saved
	try: fd = open(os.path.join(directory, filename), 'rb')
	except IOError, m:
		logStatusMsg( unicode(m) + u" could not even open our just written file. leaving function..", 2)
		return None
	try: fdT = bdecode( fd.read() )
	except ValueError: fdT = False
	if fdT: 
		# maybe you want to store downloaded data in a tmp directory so you can vet it here and then pass it on to wherever
		# os.rename( os.path.join(directory, filename), os.path.join('/my/other/directory', filename) )
		# if we successfully bdecoded the data, means that it is a torrent and we can exit, otherwise
		return True
	# the url for this download should be the last one added to saved. could try checking against rssItemNode['link'] to be sure
	else:
		logStatusMsg(u"The file %s wasn't actually torrent data. Attempting to remove from queue. Will add to failedDown" % filename , 1)
		try: os.unlink( os.path.join(directory, filename) )
		except OSError: logStatusMsg(u"could not remove file from disk: %s" % filename, 1 )	
		saved.failedDown.append( FailedItem( saved.downloads.pop(), threadName, rssItemNode, downloadDict) )
		# if using rss, remove the rss entry for the items
		global rss
		if rss: rss.delItem()
		return False

def currentOnly(directory, filename, rssItemNode, retrievedLink, downloadDict, threadName):
	if time.time() - time.mktime( rssItemNode['updated_parsed'] ) > 86400:
		try: os.unlink( os.path.join(directory, filename) )
		except OSError: logStatusMsg(u"could not remove file from disk: %s" % filename, 1 )	
		global rss
		if rss: rss.delItem()
	
def noRss(directory, filename, rssItemNode, retrievedLink, downloadDict, threadName):
	global rss
	if rss: rss.delItem()

def rmObj(directory, filename, rssItemNode, retrievedLink, downloadDict, threadName):
	if filename.endswith('.obj'):
		newfilename = filename[:-4]
		try: os.rename( os.path.join(directory, filename), os.path.join(directory, newfilename) )
		except Exception, m: logStatusMsg(u"could not remove .obj from filename %s" % filename, 2)
