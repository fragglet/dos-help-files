#!/bin/sh

find *.hlp -type f -name '*.html' | while read filename; do
	echo "https://fragglet.github.io/dos-help-files/$filename"
done | sort -f > sitemap.txt

