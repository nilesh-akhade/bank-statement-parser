#!/bin/bash
infile=$1
bank=$2
password=$3

declare -A table_coordinates=( ["hdfc"]="[0 130 600 490]" ["icici"]="[200 220 600 480]" ["citi"]="[0 50 600 200]" ["hsbc"]="[0 50 600 200]" )
table_coordinate=${table_coordinates[$bank]}

outfile="$(mktemp --suffix=.pdf)"
read -p "Removing password protection"
qpdf --password=$password --decrypt $infile $outfile
read -p "Removing unnecessary pages"
pdfcpu collect -pages 1 $outfile # TODO: Support multi page stmt
read -p "Cropping tables"
pdfcpu crop -- "$table_coordinate" $outfile
read -p "Putting tables on a new pdf"
echo "Save PDF using 'Print To File' printer"
xdg-open $outfile
printed_file=$HOME/Documents/$(basename -- "$outfile")
csvfile=$(basename -- "$infile")
read -p "Extracting data from tables: $printed_file to $csvfile"
camelot --format csv --output $csvfile stream $printed_file
