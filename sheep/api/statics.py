#!/usr/bin/python
# encoding: UTF-8

"""
static_files url replace
"""

__all__ = ['static_files', 'public_files', 'upload_files']

static_files = public_files = upload_files = lambda path: path
