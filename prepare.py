import re
import sys
import gzip
from typing import Match, Union
from astropy.time import Time
from datetime import datetime
from dateutil import parser, tz

LANG_REGEX = re.compile('"@\w{2,3}(-[\w\d]*)?')
DEFAULT_DATE = datetime(1, 1, 1, 0, 0, 0, 0, tz.UTC)
TIME_SCHEMA = '<http://www.w3.org/2001/XMLSchema#int>'
ADS_PREDICATE = '<http://rdf.freebase.com/ns/user.xandr.webscrapper.domain.ad_entry.ads_topic>'

G_YEAR = "<http://www.w3.org/2001/XMLSchema#gYear>\t.\n"
G_YEAR_MONTH = "<http://www.w3.org/2001/XMLSchema#gYearMonth>\t.\n"
DATE = "<http://www.w3.org/2001/XMLSchema#date>\t.\n"
DATE_TIME = "<http://www.w3.org/2001/XMLSchema#dateTime>\t.\n"

def time_to_seconds(string: str) -> int:
    """Converts time string to seconds since 00:00
    >>> time_to_seconds("T00")
    0
    >>> time_to_seconds("T01:00")
    3600
    >>> time_to_seconds("T10:00Z")
    36000
    >>> time_to_seconds("T10:30:30")
    37830
    """

    coefficients = [3600, 60, 1]
    parts = string.replace('T', '').replace('Z', '').split(':')
    seconds = sum([int(part) * coefficients[i] for i, part in enumerate(parts)])
    return seconds

def time_to_unix(string: str) -> int:
    """Converting date / datetime strings to unix time
    If the date is earlier, than 4799BC, jyear format is used
    >>> time_to_unix("1970-01-01")
    0
    >>> time_to_unix("2001-10-13")
    1002931200
    >>> time_to_unix("-2001-10-13")
    -125288035200
    >>> time_to_unix("-5001")
    -219988029600
    """
    is_bc = string.startswith('-')
    
    #handling pre 4799BC dates
    if is_bc and len(string) == 5 and int(string) <= -4800:
        return int(Time(int(string), format='jyear', scale='utc').unix)
    
    epoch = '-' if is_bc else '+'
    if is_bc:
        string = string[1:]
    if string.startswith('0000'):
        string = string.replace('0000', '0001', 1)
    
    # fixing "0023-07" format
    if len(string) == 7:
        string += '-01'

    parsed_time = parser.parse(string, default=DEFAULT_DATE).astimezone(tz.UTC).strftime("%Y-%m-%dT%X")   
    offset = Time(epoch + parsed_time.zfill(20), format='fits').unix
    return int(offset)

def prepare_subject(seconds: int) -> str:
    """Formatting subject for time predicates
    >>> prepare_subject(0)
    '"0"^^<http://www.w3.org/2001/XMLSchema#int>'
    >>> prepare_subject(-1000)
    '"-1000"^^<http://www.w3.org/2001/XMLSchema#int>'
    """
    return f'"{seconds}"^^{TIME_SCHEMA}'

def is_ads_topic(string: str) -> bool:
    """Checks if string contains ads predicate
    >>> is_ads_topic("<http://rdf.freebase.com/ns/award.award_winner>	<http://rdf.freebase.com/ns/type.type.instance>	<http://rdf.freebase.com/ns/m.07vdfxq>	.")
    False
    >>> is_ads_topic("<http://rdf.freebase.com/ns/m.0g4yvxb>	<http://rdf.freebase.com/ns/user.xandr.webscrapper.domain.ad_entry.ads_topic>	<http://rdf.freebase.com/ns/m.0cvhdpt>	.")
    True
    """
    return ADS_PREDICATE in string

def is_language_present(string: str) -> Union[Match, None]:
    """Checks if triplet contains the language tag
    >>> is_language_present('<http://rdf.freebase.com/ns/g.11b5lzsmmj>	<http://rdf.freebase.com/ns/common.notable_for.display_name>	"Спортивна асоціація"@uk	.')
    <re.Match object; span=(127, 131), match='"@uk'>
    >>> is_language_present('<http://rdf.freebase.com/ns/g.11b5lx1872>	<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>	<http://rdf.freebase.com/ns/common.notable_for>	.') is None
    True
    """
    return LANG_REGEX.search(string)

def is_subject_datetime(string: str) -> bool:
    """Checks if triplet has date, time or datetime as a subject
    >>> is_subject_datetime('<http://rdf.freebase.com/ns/g.124xwg2bc>	<http://rdf.freebase.com/ns/architecture.structure.opened>	"1931-02-20"^^<http://www.w3.org/2001/XMLSchema#date>\\t.\\n')
    True
    >>> is_subject_datetime('<http://rdf.freebase.com/ns/g.11b5lzsmmj>	<http://rdf.freebase.com/ns/common.notable_for.display_name>	"Спортивна асоціація"@uk\\t.\\n')
    False
    """
    return string.endswith(G_YEAR) or string.endswith(G_YEAR_MONTH) or string.endswith(DATE) or string.endswith(DATE_TIME)


def prepare() -> None:
    with gzip.open('input/freebase-rdf-latest.gz','rt') as freebase, open("output/freebase.schema", "a") as schema:
        predicates_with_lang = set()
        for line in freebase:
            if is_subject_datetime(line):
                parts = line.split('\t')
                obj = parts[2]
                value = obj.split('"^^')[0][1:]
                if obj.startswith('"T'):
                    seconds = time_to_seconds(value)
                    parts[2] = prepare_subject(seconds)
                else:
                    offset = time_to_unix(value)
                    parts[2] = prepare_subject(offset)
                sys.stdout.write('\t'.join(parts))
            else:
                if is_language_present(line):
                    predicate = line.split('\t')[1]
                    if predicate not in predicates_with_lang:
                        predicates_with_lang.add(predicate)
                        schema.write(f'{predicate}:\tstring\t@lang\t.\n')
                if not is_ads_topic(line):
                    sys.stdout.write(line)

if __name__ == '__main__':
    prepare()
