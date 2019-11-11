How to run the code:
1. Clone the repository `git clone git@github.com:eawer/freebase-to-dgraph.git`
2. Go into its folder `cd freebase-to-dgraph`
3. Save Freebase dump to `input` folder `wget -P input/ http://commondatastorage.googleapis.com/freebase-public/rdf/freebase-rdf-latest.gz`
4. Create `output` dir `mkdir output`
5. Run `python prepare.py | pigz > output/freebase_clean.rdf.gz`

Why do you need to clean the freebase dump and generate the schema before you can import Freebase into Dgraph:
1. Dgraph requires schema for subjects of certain types. In the case of Freebase, we need to add schema for triples, where the subject is a literal with a language tag, e.g., "'<http://rdf.freebase.com/ns/g.11b5lzsmmj>  <http://rdf.freebase.com/ns/common.notable_for.display_name>    "Спортивна асоціація"@uk    .'"
2. Another issue is schema-related, as well. Dgraph requires subjects to be either literal or UID. In Freebase, there are triples, with "<http://rdf.freebase.com/ns/user.xandr.webscrapper.domain.ad_entry.ads_topic>" predicate, where some subjects are UID while others are literals. Such triples were deleted from the dataset to match Dgraph rules.
3. The main issue with Dgraph is that it uses RFC 3339 for dates parsing while Freebase has lots of different date/time formats. Here are some of them:
```
   T00
   T01:00
   T10:00Z
   T10:30:30
   2001-10-13
   1810
   -0410
   -0099-12
   -0216-06-22
   2014-05
   1988-06-29T02
   2010-06-24T16:00
   2007-06-19T12:24Z
   2007-10-09T20:22:05
   2006-05-29T03:00:00Z
   1986-03-05T09:03+01:00
   2007-09-24T00:39:42.45Z
   1975-05-15T22:00:00.000Z
   2011-03-26T06:34:55.0000Z
   2007-01-24T06:18:03.046839
   2007-03-20T07:05:01.913933Z
```
Some of these formats (like "-0410", "2014-05", "T10:00Z") aren't compatible with standard mentioned above, so the date/datetime strings were converted to Unix time. Conversion algorithm looks like this:
1. The default date is set to "0001-01-01-T00:00:00.000000Z"
2. If date string is missing some parts - missing parts are taken from the default date. Example - "2014-05" is considered to be "2014-05-01T00:00:00.000000Z"    
3. If the date is earlier than 4799BC, "jyear" format is used. The reason for this is that algorithm, that used for Gregorian to Julian calendar does not work with dates before 4799 January https://github.com/liberfa/erfa/blob/master/src/cal2jd.c#L27 (according to Standards of Fundamental Astronomy http://www.iausofa.org/).
4. Conversion to Unix time
   
After performing all steps, we'll receive a prepared RDF file along with schema sufficient to import the Freebase into Dgraph.
