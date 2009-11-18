TYPE_MAP = {
    'char': 'Char',
    'unsigned short int': 'UShort',
    'long long unsigned int': 'ULLong',
    'void': 'Void',
    'signed int': 'Int',
    'unsigned int': 'UInt',
    'long int': 'Long',
    'long long int': 'LLong',
    'short unsigned int': 'UShort',
    'guint32': 'UInt32',
    'guint16': 'UInt16',
    'gpointer': 'Pointer',
    '__u16': 'UInt16',
    '__u32': 'UInt32',
    '__u64': 'UInt64',
    'short int': 'Short',
    'unsigned long': 'ULong',
    'unsigned long int': 'ULong',
    'long unsigned int': 'ULong',
#    'long long': 'c_longlong',
#    'long long int': 'c_longlong',
#    'unsigned long long int': 'c_ulonglong',
#    'unsigned long long': 'c_ulonglong',
    'signed char': 'Char',
    'unsigned char': 'UChar',
    'signed short': 'Short',
    'unsigned short': 'UShort',
    'float': 'Float',
    'double': 'Double',
    'size_t': 'SizeT',
    'int8_t': 'Int8',
    'int16_t': 'Int16',
    'int32_t': 'Int32',
    'int64_t': 'Int64',
    'uint8_t': 'UInt8',
    'uint16_t': 'UInt16',
    'uint32_t': 'UInt32',
    'uint64_t': 'UInt64',
    'wchar_t': 'WChar',
    'u_char': 'UChar',
    'u_int': 'UInt',
    'u_long': 'ULong',
    'va_list': 'VaList',
    'gint': 'Int',
    'guint': 'UInt',
    'gdouble': 'Double',
    'gboolean': 'Bool',
    'gchar': 'Char',
    'gchar*': 'String',
    'gstring': 'GString', # TODO?
    'gunichar': 'Int32', # TODO?
    'gunichar2': 'Int16', # TODO?
    'gsize': 'SizeT',
    'gssize': 'SSizeT',
    'gshort': 'Short',
    'gushort': 'UShort',
    'short': 'Short',
    'ushort': 'UShort',
    'utf8': 'String',
    'any': 'Pointer',
    'int': 'Int',
    'uint': 'UInt',
    'int8': 'Int8',
    'uint8': 'UInt8',
    'int16': 'Int16',
    'uint16': 'UInt16',
    'int32': 'Int32',
    'uint32': 'UInt32',
    'int64': 'Int64',
    'uint64': 'UInt64',
    'double': 'Double',
    'long': 'Long',
    'ulong': 'ULong',
    'glong': 'Long',
    'gulong': 'ULong',
    'long double': 'LDouble',
    'time_t': 'TimeT', # TODO: include `os/Time`
#    'ptrdiff_t': 'c_ptrdiff_t',  # Requires definition in preamble
    'POINTER(STRUCT(locale_data))': 'Pointer', # evil!
}
