#!/bin/sh

find *.hlp -type f -name '*.html' | while read filename; do
	# Don't include redirect pages in the index:
	if ! grep -q "meta http-equiv" "$filename"; then
		echo "https://fragglet.github.io/dos-help-files/$filename"
	fi
done | sort -f > sitemap.txt

