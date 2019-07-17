# -*- coding: utf-8 -*-
"""Crawl author, affiliation, contribution and other information from PNAS"""

import csv
import pkgutil
import os
import sys
import re

import scrapy


class PNASSpider(scrapy.Spider):
    """Crawl author, affiliation, contribution and other information from PNAS"""
    name = "pnas"
    resource = "resources/pnas.csv"
    start_urls = []

    def __init__(self):
        super().__init__()

        loader = pkgutil.get_loader(self.name)
        if loader is None or not hasattr(loader, 'get_data'):
            return None
        mod = sys.modules.get(self.name) or loader.load_module(self.name)
        if mod is None or not hasattr(mod, '__file__'):
            return None

        parts = self.resource.split('/')
        parts.insert(0, os.path.dirname(mod.__file__))
        resource_name = os.path.join(*parts)

        with open(resource_name) as csvfile:
            reader = csv.DictReader(csvfile)
            for index, row in enumerate(reader):
                self.start_urls += ["https://doi.org/" + row['DOI']]
#                if index >= 100:
#                    break

        return None

    @staticmethod
    def get_contribution(author, contributions):
        """To parse the contribution fields"""
        contributions_list = contributions.split(':')[1].split(';')

        author_initials = ''
        short_initials = ''
        try:
            author_initials = '-'.join(''.join(
                map(lambda s: s[0] + '.', re.split(r'\W+', i)))
                                       for i in author.split('-'))
            short_initials = author_initials[:2] + author_initials[-2]
        except:
            pass


        contribution = ', '.join(contrib.split('.')[-1].strip()
                                 for contrib in contributions_list
                                 if author_initials in contrib
                                 or short_initials in contrib
                                 or author in contrib)

        return contribution

    @classmethod
    def get_affiliation(cls, aref, alist):
        """To parse the affiliations"""
        return {(
            ('', '3. ')[ref[0] == 0 and entry[0] == 0] +
            'Affiliation' + str(ref[0] + 1) +
            (str(entry[0] + 1), '')[entry[0] == 0]):
                cls.strip_info(''.join(
                    node.xpath('.//text()').get() or node.get()
                    for node in entry[1].xpath(
                        './/node()[not(self::sup)]')))
                for ref in enumerate(aref)
                for entry in enumerate(alist.xpath(
                    './/address[sup[text()=$affiliation]]',
                    affiliation=ref[1]))} or {
                        '3. Affiliation1': cls.strip_info(''.join(
                            (node.xpath('.//text()').get() or node.get())
                            for node in alist.xpath(
                                './/address/node()[not(self::sup)]'
                                )))
                    }

    @staticmethod
    def strip_info(info):
        """(Hopefully) remove any white spaces and control characters
        from the beginning and end of the strings"""
        try:
            return re.sub(r'^(\\n)*,*\s*(.*)\s*(\\n)*$', r'\2', info)
        except:
            return info

    @classmethod
    def parse(cls, response):
        """Parsing the whole webpages"""
        response.selector.remove_namespaces()

        doi = response.xpath('//meta[@name="DC.Identifier"]/@content').get()
        date = response.xpath('//meta[@name="DC.Date"]/@content').get()
        title = response.xpath('//meta[@name="DC.Title"]/@content').get()
        contributions = response.xpath(
            '//div[@id="fn-group-1"]//li/p/text()[contains(., "Author contributions")]'
        ).get()

        for order, contributor in enumerate(response.xpath('//ol[@class="contributor-list"]/li')):
            author = (contributor.xpath('./span[@class="name"]/text()').get() or
                      contributor.xpath('./span[@class="collab"]/text()').get())
            contribution = cls.get_contribution(author, contributions)

            affiliation_ref = contributor.xpath(
                './/a[@class="xref-aff"]/sup/text()'
            ).getall() or contributor.xpath(
                './/a[@class="xref-fn"]/sup/text()'
            ).getall() or contributor.xpath(
                './/a[@class="xref-aff"]/text()'
            ).getall() or contributor.xpath(
                './/a[@class="xref-fn"]/text()'
            ).getall()
            affiliation_list = response.xpath('//ol[@class="affiliation-list"]/li')
            affiliations = cls.get_affiliation(affiliation_ref, affiliation_list)

            yield {
                "1. Author": cls.strip_info(author),
                "2. Contribution": cls.strip_info(contribution),
                "4. National": cls.strip_info(
                    affiliations.get('3. Affiliation1').split(';')[0].split(',')[-1]),
                "5. Order": order + 1,
                "6. Title": cls.strip_info(title),
                "7. Doi": cls.strip_info(doi),
                "8. Date": cls.strip_info(date),
                **affiliations
            }

        next_page = response.xpath(
            '//li[not(@class="active")]/a[@data-panel-name="jnl_pnas_tab_info"]/@href'
        ).get()
        if next_page:
            yield scrapy.Request(response.urljoin(next_page))
