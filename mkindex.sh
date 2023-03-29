
echo "<html>
<body>
<h1> Microsoft Advisor Help files </h1>
<ul>"
for d in *.hlp; do
	echo "<li> <a href=\"$d/TOPIC_LIST.html\">$d</a>"
done
echo "</ul>
</body>
</html>"

