#!/usr/bin/python
# encoding: UTF-8

"""
static_files url replace
"""

__all__ = ['static_files', 'public_files', 'upload_files']

def _files(path):
    return path

static_files = public_files = upload_files = _files
