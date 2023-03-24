#!/usr/bin/env python

from __future__ import generators, division, print_function, unicode_literals
from xml.sax.saxutils import escape, unescape
import os
import sys
import re

DOTCMD_RE = re.compile(r"^\.([a-z]+)(\s+(.*))?")

FORMAT_SWITCH_RE = re.compile(r"\\([\\ibup])", re.DOTALL)
HYPERLINK_RE = re.compile(r"\\a(.*?)\\v(.*?)\\v")
NON_HYPERLINK_RE = re.compile(r"\\v[^\\]*\\v")
ALWAYS_GREEN_RE = re.compile(u"([\u25ba\u25c4])")

DONTCARE_COMMANDS = { "freeze", "list", "paste", "popup", "ref", "mark",
                      "length", "end", "raw", "title", "command", "file",
                      "execute" }

# For filenames:
CHAR_ESCAPES = {
	"\\": "_bksl_",
	"/": "_sl_",
	"\"": "_dqt_",
	"\'": "_qt_",
	",": "_cm_",
	":": "_cln_",
	"&": "_amp_",
	"<": "_lt_",
	">": "_gt_",
	"#": "_hash_",
	".": "_dot_",
	"@": "_at_",
	" ": "_",
}

HTML_TEMPLATE="""<html>

<head>
<title>%(title)s</title>
<link rel="stylesheet" href="../style.css">
</head>

<body>
<pre>
%(body)s
</pre>
</body>

</html>
"""

REDIRECT_TEMPLATE="""<html>

<head>
<title> Page redirect </title>
<meta http-equiv="Refresh" content="0; url=%s" />
</head>

</html>
"""

TOPIC_LIST_TEMPLATE="""<html>

<head>
<title> List of Topics </title>
</head>

<body>
<h1> List of Topics </h1>
<ul>
%s
</ul>

</body>

</html>
"""

cp437 = [
# Control code range is an odd mix of symbols and real control codes:
0, 9786, 9787, 9829, 9830, 9827, 9824, 8226, 9688, 9675, 
10,  # Newline
9794, 9792,
13,  # CR
9835, 9788,

9658, 9668, 8597, 8252, 182, 167, 9644, 8616, 8593, 8595,
8594, 8592, 8735, 8596, 9650, 9660, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41,
42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60,
61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79,
80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98,
99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114,
115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 8962, 199, 252,
233, 226, 228, 224, 229, 231, 234, 235, 232, 239, 238, 236, 196, 197, 201,
230, 198, 244, 246, 242, 251, 249, 255, 214, 220, 162, 163, 165, 8359, 402,
225, 237, 243, 250, 241, 209, 170, 186, 191, 8976, 172, 189, 188, 161, 171,
187, 9617, 9618, 9619, 9474, 9508, 9569, 9570, 9558, 9557, 9571, 9553, 9559,
9565, 9564, 9563, 9488, 9492, 9524, 9516, 9500, 9472, 9532, 9566, 9567, 9562,
9556, 9577, 9574, 9568, 9552, 9580, 9575, 9576, 9572, 9573, 9561, 9560, 9554,
9555, 9579, 9578, 9496, 9484, 9608, 9604, 9612, 9616, 9600, 945, 223, 915,
960, 931, 963, 181, 964, 934, 920, 937, 948, 8734, 966, 949, 8745, 8801, 177,
8805, 8804, 8992, 8993, 247, 8776, 176, 8729, 183, 8730, 8319, 178, 9632, 160
]

def read_as_utf8(filename):
	with open(filename, "rb") as f:
		data = f.read()
	result = []
	for c in data:
		result.append(u"%c" % cp437[ord(c)])
	return u"".join(result)

def filename_for_context(context):
	if context.lower() == "index":
		return "ACTUALLY_NAMED_%s.html" % context
	escaped = (u"".join(CHAR_ESCAPES.get(c, c) for c in context))
	# Files starting with underscore are hidden by Github Pages
	if escaped.startswith("_"):
		escaped = "x" + escaped
	return escaped + ".html"

def prettiest_string(strs):
	"""Returns string with fewest digits - most likely to be human-made."""
	best = ""
	best_cnt = 9999
	for s in strs:
		digits = len(list(x for x in s if u"0" <= x <= u"9"))
		if digits < best_cnt:
			best = s
			best_cnt = digits
	return best

class Topic(object):
	def __init__(self, db):
		self.db = db
		self.contexts = []
		self.category = None
		self.topic = u""
		self.text = u""
		self.is_toc = False

	def prettiest_context(self):
		# Try non-local contexts first.
		nonlocal_contexts = [c for c in self.contexts
		                     if not c.startswith("@")]
		if nonlocal_contexts:
			return prettiest_string(nonlocal_contexts)
		return prettiest_string(self.contexts)

	def name(self):
		if len(self.topic) > 0:
			return self.topic
		return self.prettiest_context()

	def filename(self):
		if self.is_toc:
			return "index.html"
		return filename_for_context(self.prettiest_context())

	def alias_filenames(self):
		main = self.prettiest_context()
		for c in self.contexts:
			if self.is_toc or c != main:
				yield filename_for_context(c)

	def to_html(self):
		# TODO: HTML escape < to &lt; etc.
		result = escape(self.text)
		curr = ['p']
		def switch_format(m):
			old_format, new_format = curr[0], m.group(1)
			if new_format == "\\":  # Double \\
				return new_format
			if old_format != "p":
				tag = "</%c>" % old_format
			else:
				tag = ""
			if new_format != "p":
				tag += "<%c>" % new_format
			curr[0] = new_format
			return tag
		def create_link(m):
			text, dest = m.group(1), unescape(m.group(2))
			dest = unescape(dest)
			if dest in ("!B", "!cq.hb"):
				dest = "javascript:history.back();"
			elif "!" not in dest:
				target_topic = (
					self.db.topics_by_context.get(dest))
				if target_topic is not None:
					dest = target_topic.filename()
				else:
					dest = "unknown#" + dest
			else:
				filename, context = dest.split("!", 1)
				dest = "../%s/%s" % (
					filename.lower(),
					filename_for_context(context),
				)
			return "<a href='%s'>%s</a>" % (dest, text)
		def make_green(m):
			return "<span class='grhilite'>%s</span>" % m.group(1)

		result = FORMAT_SWITCH_RE.sub(switch_format, result)
		result = HYPERLINK_RE.sub(create_link, result)
		result = NON_HYPERLINK_RE.sub("", result)
		result = ALWAYS_GREEN_RE.sub(make_green, result)
		return result

class Database(object):

	def parse_dotcmd(self, cmd, arg):
		if cmd in DONTCARE_COMMANDS:
			return
		if cmd == "category":
			self.current_topic.category = arg
		elif cmd == "topic":
			self.current_topic.topic = arg
		else:
			raise Exception("Unknown dot command %r" % cmd)

	def parse_text(self, text):
		self.current_topic = Topic(self)
		topics = []

		last_was_context = False

		for line in text.splitlines():
			m = DOTCMD_RE.match(line)
			if not m:
				self.current_topic.text += line + "\n"
				last_was_context = False
				continue

			cmdname, arg = m.group(1), m.group(3)
			if cmdname == "context":
				# New topic?
				if not last_was_context:
					self.current_topic = Topic(self)
					topics.append(self.current_topic)
				self.current_topic.contexts.append(arg)
				last_was_context = True
				continue

			self.parse_dotcmd(cmdname, arg)
			last_was_context = False

		self.current_topic = None
		self.topics = topics
		self.topics_by_context = {}
		for t in topics:
			for c in t.contexts:
				self.topics_by_context[c] = t

		# Find the ToC
		for context, topic in self.topics_by_context.items():
			if "contents" in context:
				topic.is_toc = True
				break
		else:
			print("Didn't find the table of contents ...")


def write_html_file(filename, topic):
	with open(filename, "wb") as out:
		html = HTML_TEMPLATE % {
			'body': topic.to_html(),
			'title': escape(topic.name()),
		}
		out.write(html.encode("utf-8"))

def write_redirect_file(filename, topic):
	with open(filename, "wb") as out:
		html = REDIRECT_TEMPLATE % (topic.filename(),)
		out.write(html.encode("utf-8"))

def write_topic_list(filename, db):
	with open(filename, "wb") as out:
		topic_list = []
		for topic in db.topics:
			topic_list.append((topic.name(), topic.filename()))
		html_topic_list = "\n".join(
			"<li> <a href='%s'>%s</a>" % (f, escape(t))
			for t, f in sorted(topic_list)
		)
		html = TOPIC_LIST_TEMPLATE % (html_topic_list,)
		out.write(html.encode("utf-8"))

if len(sys.argv) != 3:
	print("Usage: %s <filename> <output dir>" % sys.argv[0])

outdir = sys.argv[2]
f = read_as_utf8(sys.argv[1])
db = Database()
db.parse_text(f)
for t in db.topics:
	filename = t.filename()
	write_html_file(os.path.join(outdir, filename), t)
	for filename in t.alias_filenames():
		write_redirect_file(os.path.join(outdir, filename), t)
write_topic_list(os.path.join(outdir, "TOPIC_LIST.html"), db)

