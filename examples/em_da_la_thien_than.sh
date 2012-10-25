#!/bin/sh
python vbbfetcher.py "Em da la thien than" -I 'http://vozforums.com/showpost.php?p=51164357&postcount=1' 'http://vozforums.com/showpost.php?p=51185462&postcount=2' -r '^\s*((P\s*\d+.*)|chap\s*\d+)\s*$'
