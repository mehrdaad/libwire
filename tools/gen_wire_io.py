#!/usr/bin/env python

includes = [
        "sys/types.h",
        "sys/stat.h",
        "sys/socket.h",
        "sys/vfs.h",
        "sys/ioctl.h",
        "fcntl.h",
        "unistd.h",
        "netdb.h",
        "ifaddrs.h"
        ]

syscalls = [
        "int open(const char *pathname, int flags, mode_t mode)",
        "int close(int fd)",
        "ssize_t pread(int fd, void *buf, size_t count, off_t offset)",
        "ssize_t pwrite(int fd, const void *buf, size_t count, off_t offset)",
        "ssize_t read(int fd, void *buf, size_t count)",
        "ssize_t write(int fd, const void *buf, size_t count)",
        "int fstat(int fd, struct stat *buf)",
        "int stat(const char *path, struct stat *buf)",
        "int ftruncate(int fd, off_t length)",
        "int fallocate(int fd, int mode, off_t offset, off_t len)",
        "int fsync(int fd)",
        "int statfs(const char *path, struct statfs *buf)",
        "int fstatfs(int fd, struct statfs *buf)",
        "int getaddrinfo(const char *node, const char *service, const struct addrinfo *hints, struct addrinfo **res)",
        "int ioctl(int d, unsigned long request, void *argp)",
        "int getifaddrs(struct ifaddrs **ifap)"
        ]


import re
import sys

gen_header_file = 'h' in sys.argv[1:]
gen_c_file = 'c' in sys.argv[1:]

if not gen_header_file and not gen_c_file:
    print 'Must choose either "c" or "h"'
    sys.exit(1)

if gen_header_file and gen_c_file:
    print 'Must choose only one of "c" or "h"'
    sys.exit(2)

decl_re = re.compile(r'^([a-z_* 0-9]+[* ])([a-z0-9_]+)\((.*)\)$')
arg_re = re.compile(r'^ ?([a-z_* 0-9]+[* ])([a-z0-9_]+) ?$')

def strip_list(l):
    if type(l) == str or type(l) == unicode:
        return l.strip()
    return map(strip_list, l)

def parse_decl(decl):
    m = decl_re.match(decl)
    if m is None:
        raise BaseException("Declaration '%s' failed to parse by regex" % decl)

    ret_type, func_name, args_full = m.groups()
    args = args_full.split(',')
    argd = []
    if len(args[0]) > 0:
        for arg in args:
            m = arg_re.match(arg)
            if m is None:
                raise BaseException("Argument '%s' cannot be parsed by regex" % arg)
            argd.append(m.groups())
    ret = (ret_type, func_name, args_full, argd)
    return strip_list(ret)

parsed_decl = map(parse_decl, syscalls)

def enum_name(decl):
    return 'IO_' + decl[1].upper()

def args_call(decl):
    parts = map(lambda arg: 'act->%s.%s' % (decl[1], arg[1]), decl[3])
    return ', '.join(parts)

if gen_header_file:
    print '#ifndef WIRE_LIB_IO_GEN_H'
    print '#define WIRE_LIB_IO_GEN_H'
    print
    for inc in includes:
        print '#include <%s>' % inc
    for decl in parsed_decl:
        print '%s wio_%s(%s);' % (decl[0], decl[1], decl[2])
    print
    print '#endif'
else:
    print '#include "wire_io_gen.h"'
    print
    print 'enum wio_type {'
    for decl in parsed_decl:
        print '\t%s,' % enum_name(decl)
    print '};'
    print
    print 'struct wire_io_act {'
    print '    struct wire_io_act_common common;'
    print '    enum wio_type type;'
    print '    union {'
    for decl in parsed_decl:
        print '        struct {'
        for arg in decl[3]:
            print '            %s %s;' % (arg[0], arg[1])
        print '            %s ret;' % decl[0]
        print '            int verrno;'
        print '        } %s;' % decl[1]
    print '    };'
    print '};'
    print
    print 'static void perform_action(struct wire_io_act *act)'
    print '{'
    print '    switch (act->type) {'
    for decl in parsed_decl:
        print '        case %s:' % enum_name(decl)
        print '            act->%s.ret = %s(%s);' % (decl[1], decl[1], args_call(decl))
        print '            act->%s.verrno = errno;' % decl[1]
        print '            break;'
    print '    }'
    print '}'
    print
    for decl in parsed_decl:
        print '%s wio_%s(%s)' % (decl[0], decl[1], decl[2])
        print '{'
        print '    struct wire_io_act act;'
        print '    act.type = %s;' % enum_name(decl)
        for arg in decl[3]:
            print '    act.%s.%s = %s;' % (decl[1], arg[1], arg[1])
        print '    wakeup_fd_listener();'
        print '    submit_action(&wire_io, &act.common);'
        print '    if (act.%s.ret < 0)' % decl[1]
        print '        errno = act.%s.verrno;' % decl[1]
        print '    return act.%s.ret;' % decl[1]
        print '}'
        print