#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    DocBook to ReST converter for CESM documentation
    =========================
    This script is a one-off for converting CESM-style 'docbook'
    documents to ReST.

"""

# Python 3 compatible printing in Python 2.
from __future__ import print_function
import sys
import re
import argparse
import subprocess
import shutil
import os
import os.path

# Globals (since this is meant to be a one-off sript)
fulltagRE  = re.compile(r"<([^>]+)>([^<]*)</\1>")
opentagRE  = re.compile(r"(<[^>]+>)")
codeItemRE = re.compile(r"&([^;]+);")
doctypeRE =  re.compile(r"^[ ]*<!DOCTYPE ")
ignore_tags = ( '?xml', 'para', '/chapter', '/sect1', '/sect2', '/sect3' )
stringsubs = { '&lt;'         : '<',    '&gt;'          : '>',
               '<command>'    : '``',   '</command>'    : '``',
               '<acronym>'    : '**',   '</acronym>'    : '**',
               '<envar>'      : '``**', '</envar>'      : '**``',
               '<filename>'   : '``',   '</filename>'   : '``',
               '<classname>'  : '``',   '</classname>'  : '``',
               '<methodname>' : '``',   '</methodname>' : '``',
               '<varname>'    : '``',   '</varname>'    : '``',
               '<userinput>'  : '``*',  '</userinput>'  : '*``',
               '</para>'      : '\n',   '<note>'        : '.. note::' }
sectMarkers = { 'chapter' : '################################################',
                'sect1'   : '------------------------------------------------',
                'sect2'   : '^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^',
                'sect3'   : '""""""""""""""""""""""""""""""""""""""""""""""""'}
overbarSect = [ 'chapter', 'sect1' ]
lastSect = None
preamble = """
.. toctree::
   :maxdepth: 3
   :titlesonly:
   :glob:
"""


def _main():
  aliases = {}
  # Create an argument parser and parse command line arguments
  parser = argparse.ArgumentParser(usage='project [options]',
                                   description='Convert a docbook document to a Sphinx ReST document')
  parser.add_argument('project', help='Project name, also name of document')
  parser.add_argument('-d', '--docbook-source',
                      help='Main docbook document name')
  parser.add_argument('--destination', default='doc',
                      help='New directory for ReST version of document')
  struct = parser.add_argument_group('Structure options')
  struct.add_argument('--no-sep',
                      help='if specified, do not separate source and build dirs')
  struct.add_argument('--dot', default="_",
                      help='replacement for dot in _templates etc.')
  basic = parser.add_argument_group('Project basic options')
  basic.add_argument('-a', '--author', default="'CESM Software Engineering Group'",
                     help='copyright holder')
  basic.add_argument('-v', default='1.0.0', help='version of project')
  basic.add_argument('-r', '--release', default='1.0.0', 
                     help='release of project')
  basic.add_argument('-l', '--language', default='en', help='document language')
  basic.add_argument('--suffix', default='.rst', help='source file suffix')
  basic.add_argument('--master', help='master document name')
  basic.add_argument('--epub', help='use epub')
  ext = parser.add_argument_group('Extension options')
  ext.add_argument('--ext-autodoc', help='enable autodoc extension')
  ext.add_argument('--ext-doctest', help='enable doctest extension')
  ext.add_argument('--ext-intersphinx', help='enable intersphinx extension')
  ext.add_argument('--ext-todo', help='enable todo extension')
  ext.add_argument('--ext-coverage', help='enable coverage extension')
  ext.add_argument('--ext-imgmath', help='enable imgmath extension')
  ext.add_argument('--ext-mathjax', help='enable mathjax extension')
  ext.add_argument('--ext-ifconfig', help='enable ifconfig extension')
  ext.add_argument('--ext-viewcode', help='enable viewcode extension')
  ext.add_argument('--ext-githubpages', help='enable githubpages extension')
  make = parser.add_argument_group('Makefile and Batchfile creation')
  make.add_argument('--makefile', default='y', help='create makefile')
  make.add_argument('--no-makefile', help='not create makefile')
  make.add_argument('--batchfile', help='create batchfile')
  make.add_argument('--no-batchfile', default='y', help='do not create batchfil\
e')
  make.add_argument('-M', '--no-use-make-mode',
                    help='not use make-mode for Makefile/make.bat')
  make.add_argument('-m', '--use-make-mode',
                    help='use make-mode for Makefile/make.bat')
  args = parser.parse_args()

  # Create an argument list for a call to sphinx-quickstart
  sqsargs = [ 'sphinx-quickstart' ]
  sqsargs.append(args.destination)
  if (args.no_sep is None):
    sqsargs.append('--sep')
  else:
    sqsargs.append('--no-sep')
  # End if
  # To keep sphinx-quickstart from querying on missing extensions, go quiet
  sqsargs.append('--quiet')
  sqsargs.extend(('--dot', args.dot))
  sqsargs.extend(('--project', args.project))
  sqsargs.extend(('--author', args.author))
  sqsargs.extend(('-v', args.v))
  sqsargs.extend(('--release', args.release))
  sqsargs.extend(('--language', args.language))
  sqsargs.extend(('--suffix', args.suffix))
  if (args.master is not None):
    sqsargs.extend(('--master', args.master))
  else:
    sqsargs.extend(('--master', args.project))
  # End if
  if (args.epub is not None):
    sqsargs.append('--epub')
  # End if
  if (args.ext_autodoc is not None):
    sqsargs.append('--ext-autodoc')
  # End if
  if (args.ext_doctest is not None):
    sqsargs.append('--ext-doctest')
  # End if
  if (args.ext_intersphinx is not None):
    sqsargs.append('--ext-intersphinx')
  # End if
  if (args.ext_todo is not None):
    sqsargs.append('--ext-todo')
  # End if
  if (args.ext_coverage is not None):
    sqsargs.append('--ext-coverage')
  # End if
  if (args.ext_imgmath is not None):
    sqsargs.append('--ext-imgmath')
  # End if
  if (args.ext_mathjax is not None):
    sqsargs.append('--ext-mathjax')
  # End if
  if (args.ext_ifconfig is not None):
    sqsargs.append('--ext-ifconfig')
  # End if
  if (args.ext_viewcode is not None):
    sqsargs.append('--ext-viewcode')
  # End if
  if (args.no_makefile is not None):
    sqsargs.append('--no-makefile')
  else:
    sqsargs.append('--makefile')
  # End if
  if (args.no_batchfile is not None):
    sqsargs.append('--no-batchfile')
  else:
    sqsargs.append('--batchfile')
  # End if
  if (args.no_use_make_mode is not None):
    sqsargs.append('--no-use-make-mode')
  # End if
  if (args.use_make_mode is not None):
    sqsargs.append('--use-make-mode')
  # End if

  # Remove the project directory if it exists
  try:
    if (os.path.exists(args.destination)):
      print("Removing ",args.destination)
      shutil.rmtree(args.destination)
    # End if
  except Exception as e:
    print(e)
  # End try
  # Run sphinx-quickstart
  subprocess.check_call(sqsargs)

  # Read in the main document (if specified)
  if ((args.docbook_source is not None) and os.path.exists(args.docbook_source)):
    dst_path = os.path.join(args.destination, 'source')
    subdocs = _translate_docbook_source(args.docbook_source, dst_path,
                                        aliases, master=True)
    while (len(subdocs) > 0):
      doc = subdocs.pop(0)
      subdoc = doc[1]
      if (not os.path.exists(subdoc)):
        trysub = os.path.join(os.path.dirname(args.docbook_source), subdoc)
        if (os.path.exists(trysub)):
          print('Replacing "%s" with "%s"'%(subdoc,trysub))
          subdoc = trysub
        else:
          _error('Referenced sub-document, "%s", is not found'%subdoc)
        # End if
      # End if
      subdocs.extend(_translate_docbook_source(subdoc, dst_path, aliases))
    # End for
  # End if
# End def _main

def _fl_out(tipe, linenum, filename):
  sys.stderr.write('%s: line %d of %s'%(tipe, linenum, filename))
# End def _fl_out

def _warn(s, linenum, filename):
  _fl_out('WARNING', linenum, filename)
  sys.stderr.write(": %s\n" % s)
# End def _warn

def _error(s, linenum, filename):
  _fl_out('ERROR', linenum, filename)
  sys.stderr.write(": %s\n" % s)
  exit()
# End def _error

def _warn_single_tag(tag, ntags, linenum, filename):
  if (ntags > 1):
    _warn("<%s> should on line by itself, ignoring other tags\n" % tag,
          linenum, filename)
  # End if
# End def _warn_single_tag

def _translate_string(str, strtags, aliases, section, indent, linenum, filename):
  global lastSect
  indents   = [ '<note>' ]
  unindents = [ '/note' ]
  # Looking for tags and other syntax to translate from docbook to ReST

  for trigger in stringsubs.keys():
    if (str.find(trigger) >= 0):
      str = stringsubs[trigger].join(str.split(trigger))
      if (trigger in indents):
        indent = indent+'  '
      # End if
    # End if
  # End for

  if (aliases is not None):
    for trigger in aliases.keys():
      if (str.find(trigger) >= 0):
        str = aliases[trigger].join(str.split(trigger))
      # End if
    # End for
  # End if

  if (strtags is not None):
    for tag in strtags:
      if (tag[0] in sectMarkers.keys()):
        lastSect = tag[0]
        if (tag[1] != 'id'):
          _error('%s tag with missing id'%tag[0], linenum, filename)
        # End if
        sectID = tag[2]
        # Assume entire line is section tag and remove it (add blank lines)
        str = "\\n.. _"+_strip_quotes(sectID)+":\\n"
      # End if
      if (tag[0] == 'title'):
        if (lastSect is None):
          _error('<title>tag with no preceding section tag', linenum, filename)
        # End if
        str = ''.join(str.strip().split('<title>'))
        if (lastSect in overbarSect):
          str = sectMarkers[lastSect]+'\n'+str.strip()
        # End if
      # End if
      if (tag[0] == '/title'):
        if (lastSect is None):
          _error('</title>tag with no preceding section tag', linenum, filename)
        # End if
        str = ''.join(str.strip().split('</title>'))
        str = str.strip()+'\n'+sectMarkers[lastSect]
        lastSect = None
      # End if
      if (tag[0] in unindents):
        str = ''.join(str.strip().split('<'+tag[0]+'>'))
        indent = indent[0:len(indent)-2]
      # End if
    # End for
  # End if

  return str.strip(), section, indent
# End def _translate_string

def _set_postline(tags, linenum, filename):
  postline = None
  for tag in tags:
    if (tag in sectMarkers.keys()):
      _warn_single_tag(tag, len(tags), linenum, filename)
      postline = sectMarkers[tag]
      break
    # End if
  # End for
  return postline
# End def _set_postline

def _translate_filename(filename, dest_path, remove_old = False):
  # Strip .xml ending if it is there
  fname = filename.rsplit('.', 1)
  if (fname[1] == 'xml' or fname[1] == 'XML'):
    filename = fname[0]
  # No else because if the ending is not .xml, just leave it alone
  # End if
  filename += '.rst'
  dest_file = os.path.join(dest_path, filename)
  if (remove_old and os.path.exists(dest_file)):
    os.remove(dest_file)
  # End if
  try:
    os.makedirs(os.path.dirname(dest_file), 0755 )
  except OSError:
    pass # Probably only get here if directory already exists
  return dest_file
# End def _translate_filename

def _translate_docbook_source(src_file, dest_path, alias_list, master=False):
  subdocs = [] # Cannot use dictionary because order matters
  filename = os.path.basename(src_file)
  inDOCTYPE = False
  inBook = False
  linenum = 0
  dest_file = _translate_filename(filename, dest_path, True)
  linein = ''
  indent = ''
  with open(src_file, "rU") as sf, open(dest_file, "w+") as df:
    for line in sf:
      linein += " " + line.strip()
      linenum = linenum + 1
      lineout = None
      section = None
      linein, ltags = _complete_line(linein, linenum, filename)
      if ((ltags is not None) or 
          (doctypeRE.match(linein.strip()) is not None) or
          (linein.strip().find(']>') > -1)):
        if (ltags is None):
          ltags = []
        # End if
        etags = [ _x[0] for _x in ltags ]
        if (doctypeRE.search(linein) is not None):
          if (inDOCTYPE):
            _error('Nested DOCTYPE tags', linenum, filename)
          else:
            inDOCTYPE = True
            linein = '' # Ignore this line
          # End if
        elif (inDOCTYPE):
          # Here, we only process !ENTITY tags
          if ('!ENTITY' in etags):
            _warn_single_tag('!ENTITY', len(etags), linenum, filename)
            entag = [ _x for _x in ltags if _x[0] == '!ENTITY' ][0]
            if (len(entag) < 2):
              _warn('Malformed !ENTITY tag', linenum, filename)
            elif ((len(entag) > 3) and (entag[2] == 'SYSTEM')):
              # We have a new subdoc but it may be a partial path
              subdocs.append((entag[1], _strip_quotes(entag[3])))
            elif (len(entag) > 2):
              # Treat this as an alias
              newkey = "&" + entag[1] + ";"
              alias_list[newkey] = _strip_quotes(_translate_string(entag[2], None, None, None, indent, linenum, filename)[0])
            # End if
          elif ((len(ltags) == 0) and (linein.find(']>') >= 0)):
            inDOCTYPE = False
          else:
            if (len(linein.strip()) > 0):
              _warn('Unnkown line in DOCTYPE section', linenum, filename)
            # End if
          # End if
          linein = '' # Always pretend we successfully handled this line (hack?)
        elif ('book' in etags):
          if (inBook):
            _error('Nested book tags', linenum, filename)
          else:
            _warn_single_tag('book', len(etags), linenum, filename)
            inBook = True
            if (master) :
              print(preamble, file=df)
            # End if
            linein = '' # Ignore this line
            lineout = ''
          # End if
        elif ('/book' in etags):
          if (not inBook):
            _error('End book tag found before opening tag', linenum, filename)
          else:
            _warn_single_tag('/book', len(etags), linenum, filename)
            inBook = False
          # End if
          linein = ''
        elif (inBook):
          cmatch = codeItemRE.search(linein)
          if (cmatch is not None):
            # Insert doc here
            filesym = cmatch.group(1)
            # Find the filename for filesym
            fmatch = [ _x[1] for _x in subdocs if _x[0] == filesym ]
            if (len(fmatch) > 0):
              sub_file = _translate_filename(fmatch[0], dest_path, True)
              sub_file = os.path.basename(sub_file)
              lineout = '   ' + sub_file
            # End if
          else:
            lineout, section, newindent = _translate_string(linein, ltags, alias_list, section, indent, linenum, filename)
          # End if
          linein = '' # Assume line handled successfully
        else:
          lineout, section, newindent = _translate_string(linein, ltags, alias_list, section, indent, linenum, filename)
          linein = '' # Assume line handled successfully
        # End if (line match)
      else: # just add in next line
        pass
      # End if (not incomplete line)
      if (lineout is not None):
        print(indent+'\n'.join(lineout.split('\\n')), file=df)
        lineout = None
        linein = ''
        indent = newindent
      # End if
    # End for
  # End with
  return subdocs
# End def _translate_docbook_source

def _strip_quotes(string):
  # Make sure this is a quoted string
  strb = 0
  stre = len(string) - 1
  if (((string[strb] == '"') and (string[stre] == '"')) or
      ((string[strb] == "'") and (string[stre] == "'"))):
    return string[strb+1:stre]
  else:
    return string
  # End if
# End def _strip_quotes

def _find_strings(line):
  locs = list()
  in_s_string = False
  in_l_string = False
  index = 0

  while (index < len(line)):
    if (in_s_string):
      if (line[index] == "'"):
        in_s_string = False
        locs.append((lb, index))
      # End if
    elif (in_l_string):
      if (line[index] == '"'):
        in_l_string = False
        locs.append((lb, index))
      # End if
    else:
      if (line[index] == "'"):
        in_s_string = True
        lb = index
      elif (line[index] == '"'):
        in_l_string = True
        lb = index
      # No else
      # End if
    # End if
    index = index + 1
  # End while

  return locs, (in_s_string or in_l_string)
# End def _find_strings

def _in_string(start, end, locs):
  send = -1

  for (ls, le) in locs:
    if ((ls <= start) and (le >= end)):
      send = le
      break
    # End if
  # End for

  return send
# End def _in_string

def _read_tags(line, linenum, filename):
  tags = []
  index = 0
  inds = len(line)
  inde = -1
  # First, we need to know where the strings are
  string_locs, incomplete = _find_strings(line)
  level = -1 if incomplete else 0
  while(index < len(line)):
    str_end = _in_string(index, index, string_locs)
    if (str_end > -1):
      index = str_end
    elif (line[index] == '<'):
      if (level == 0):
        inds = index + 1
      # End if
      level = level + 1
    elif (line[index] == '>'):
      level = level - 1
      if (level == 0):
        inde = index
        if (inds < inde):
          newtag = list()
          # Note, there could be spaces inside a string
          tagb = inds
          for (strb, stre) in string_locs:
            # Is there stuff before this string (there should be before first)
            if ((strb >= inds) and (stre <= inde)):
              if (tagb < strb):
                tage = strb - 1
                newtag.extend(line[tagb:tage].strip().split(" "))
              # End if
              # Append string
              newtag.append(line[strb:stre+1])
              tagb = stre + 1
            # End if
          # End for
          if (inde > tagb):
            newtag.extend(line[tagb:inde].strip().split(" "))
          # End if
          if (newtag[0] in ignore_tags):
            # We need to pretend this whole tag isn't there
            line = line[0:inds-1].rstrip() + " "
            index = len(line)
            line = line + line[inde+1:].lstrip()
          else:
            # Remove empty newtag elements, then append
            newtag = [ _x for _x in newtag if len(_x) > 0]
            tags.append(newtag)
            index = inde
          # End if
          inds = len(line)
          inde = -1
        else:
          _error('Internal Error?', linenum, filename)
        # End if
      # No else, this is an embedded tag close
      # End if
    # End if, just consume one more character
    index = index + 1
  # End while

  return line, tags, (level != 0)
# End def _read_tags

def _incomplete_tags(tags, linenum, filename):
  # We are only interested in tags which we need to process atomically.
  tagopens = ('link', 'ulink', 'bookinfo')
  tagcloses = [ '/'+_x for _x in tagopens ]
  matches = {}
  for pb in tagopens:
    matches[pb] = True
  # End for
  for tag in tags:
    if (tag[0] in tagopens):
      if (matches[tag[0]]):
        matches[tag[0]] = False
      else:
        _warn('open tag after close tag for %s?'%tag[0], linenum, filename)
      # End if
    elif (tag[0] in tagcloses):
      if (matches[tag[0][1:]]):
        _warn('close tag before open tag for %s?'%tag[0], linenum, filename)
      else:
        matches[tag[0][1:]] = True
      # End if
    # End if
  # End for
  return (False in matches.values())
# End def _incomplete_tags

def _complete_line(line, linenum, filename):
  tags = None
  newline = line.strip()
  if (len(newline) > 0):
    locs, incomplete = _find_strings(newline)
    if (not incomplete):
      newline, tags, incomplete = _read_tags(newline, linenum, filename)
      if (incomplete or _incomplete_tags(tags, linenum, filename)):
        tags = None
        newline = line.strip()
      # End if
    # End if
  # End if
  return newline, tags
# End def _complete_line

# # Tags to simply ignore
# keyword = _concat
# keywordset = _concat
# abstract = _concat
# bookinfo = _concat
# corpauthor = _concat
# example = _concat
# glossary = _concat
# figure = _concat
# computeroutput = userinput
# literal = userinput
# option = userinput
# procedure = orderedlist
# productname = emphasis
# programlisting = screen
# pubdate = emphasis
# quote = userinput
# simpara = _block_separated_with_blank_line

if __name__ == '__main__':
   _main()
# End if
