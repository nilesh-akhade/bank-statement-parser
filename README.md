# Bank Statement Parser

A CLI tool which allows to extract structured transactions data from Bank or Credit card statements in PDF format.

## Problem

It might be necessary to classify, tag transactions done from credit cards for the purpose of personal finance management. Unfortunately indian bank and credit card lenders do not provide statements in machine readable formats. Hence we are left with parsing PDF files.

## Design

Extracting text content from PDF is not simple because it always produces hard to understand text stream. Obviously because PDF is printing optimized format, it lacks structure and whitespace information.

    pdfcpu extract -mode=content hdfc_cc.pdf

My approach is to crop the PDF file pages to include only the table part. And then provide this PDF file to the library which is capable of extracting tables from PDF.

## Available Libraries and Tools

- [pdfcpu](https://github.com/pdfcpu/pdfcpu) - A PDF processor written in Go
- [PDF Reader](https://github.com/ledongthuc/pdf) - A simple Go library which enables reading PDF files

- [Camelot](https://github.com/atlanhq/camelot): PDF Table Extraction for Humans
- [Tabula](https://github.com/tabulapdf/tabula) is a tool for liberating data tables trapped inside PDF files
- [pdfplumber](https://github.com/jsvine/pdfplumber) - Table extraction and visual debugging
- [pdftables](https://github.com/drj11/pdftables) - A library for extracting tables from PDF files
