# -*- coding: utf-8 -*-
import scrapy
import csv
import pkgutil, os, sys

class PNASSpider(scrapy.Spider):
    name = "pnas"
    resource = "resources/pnas.csv"
    start_urls = []

    def __init__(self):

        loader = pkgutil.get_loader (self.name)
        if loader is None or not hasattr (loader, 'get_data'):
            return None
        mod = sys.modules.get (self.name) or loader.load_module (self.name)
        if mod is None or not hasattr (mod, '__file__'):
            return None

        parts = self.resource.split ('/')
        parts.insert (0, os.path.dirname (mod.__file__))
        resource_name = os.path.join (*parts)


        with open (resource_name) as csvfile:
            reader = csv.DictReader(csvfile)
            for index, row in enumerate (reader):
                self.start_urls += ["https://doi.org/" + row['DOI']]
#                if index >= 100:
#                    break


    def parse(self, response):
        response.selector.remove_namespaces()

        doi = response.xpath ('//meta[@name="DC.Identifier"]/@content').get()
        date = response.xpath ('//meta[@name="DC.Date"]/@content').get()
        title = response.xpath ('//meta[@name="DC.Title"]/@content').get()
        contribution = response.xpath ('//div[@id="fn-group-1"]//li/p/text()[contains(., "Author contributions")]').get()

        for contributor in response.xpath ('//ol[@class="contributor-list"]/li'):
            author = contributor.xpath ('./span[@class="name"]/text()').get()

            ano = 1
            aff = {}
            affiliations = contributor.xpath ('.//a[@class="xref-aff"]/sup/text()').getall()
            if len (affiliations) == 0:
                affiliations = contributor.xpath ('.//a[@class="xref-aff"]/text()').getall()

            for affiliation in affiliations:
                aff = {**aff,
                        'affiliation' + str (ano): ''.join ((node.xpath ('.//text()').get() or node.get())
                            for node in response.xpath ('//ol[@class="affiliation-list"]/li/address[contains(.//sup/text(), $affiliation)]/node()[not(self::sup)]', affiliation = affiliation))
                        }
                ano += 1
            if not aff.get('affiliation1'):
                aff = {'affiliation1': ''.join ((node.xpath ('.//text()').get() or node.get())
                        for node in response.xpath ('//ol[@class="affiliation-list"]/li/address/node()[not(self::sup)]'))
                    }

            yield {
                "author": author,
                "doi": doi,
                "date": date,
                "title": title,
                "contribution": contribution,
                **aff
            }

        next_page = response.xpath ('//li[not(@class="active")]/a[@data-panel-name="jnl_pnas_tab_info"]/@href').get()
        if next_page:
            yield scrapy.Request (response.urljoin (next_page))
