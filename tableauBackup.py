import tableauserverclient as TSC
import os
import zipfile
import re
from git import Repo
import git
from datetime import datetime, timedelta
import configparser
import codecs
import keyring
import getpass
import logging
import logConfig
import argparse
import shutil
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
#parsing credentials in config.ini
cfg = configparser.ConfigParser()
cfg.read('config.ini') 

#set up logging 
logger = logging.getLogger(__name__)

#set up arguments for updating password and incremental or full load backup
parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required = True)
parser.add_argument('-p', '--password', choices = ['a', 't', 'g'], help = 'Set password for [a]ll, [t]ableau server, or [g]it')
group.add_argument('-i', '--incremental', type = int, nargs = '?', const = 1, metavar = '<hours>', help = 'Set the time period in hours to scan for any changes in Tableau Server, default is 1 aka scan for changes made in the last hour')
group.add_argument('-f', '--full-load', action = 'store_true', help = 'Back up all workbooks and datasources regardless of last updated time')
args = parser.parse_args()

os.system('git config --global core.longpaths true')

def main():

    try:
        tableauPassword = getCreds()

        logger.info('Preparing Backup')

        #setting up tableau login credentials
        tableau_auth = TSC.TableauAuth(cfg['tableauServer']['user'], tableauPassword)

        server = TSC.Server(cfg['tableauServer']['url'])
        server.add_http_options({'verify': False})
        server.use_server_version()

        firstTime = False
        
        #check if there is git repo, if not clone the repository
        oPath = cfg['git']['projectName']

        if os.path.isdir(oPath) is False:
            Repo.clone_from(cfg['git']['url'], oPath)
            firstTime = True 

        repo = git.Repo(oPath)
        
        #logging into tableau server
        server.auth.sign_in(tableau_auth)
        
        #setting time stamp for one hour previous from when this script is run 
        utc_value = int(cfg['tableauServer']['utc_value'])
        currentTime = datetime.now()

        if firstTime is True or args.full_load == True:
            downloadChangesSince = '2000-01-01T00:00:00Z'
        else:
            downloadChangesSince = (datetime.fromtimestamp((currentTime.timestamp() - (utc_value + args.incremental)*3600)).replace(microsecond = 0)).isoformat() + 'Z'

        logger.info("downloadChangesSince: {0}".format(downloadChangesSince))

        req_option = TSC.RequestOptions()
        req_option.filter.add(TSC.Filter(TSC.RequestOptions.Field.UpdatedAt,
                                    TSC.RequestOptions.Operator.GreaterThanOrEqual,
                                    downloadChangesSince))

        remove_punctuation_and_turkish_map = dict((ord(char), None) for char in '\/*?:"<>|')
        turkish_character_set = {('ı','i'), ('İ','I'), ('ü','u'), ('Ü','U'), ('ö','o'), ('Ö','O'), ('ç','c'), ('Ç','C'), ('ş','s'), ('Ş','S'), ('ğ','g'), ('Ğ','G')}
        for map_item in turkish_character_set:
            remove_punctuation_and_turkish_map.update({ord(map_item[0]): map_item[1]})
        
        #iterating through each site on tableau
        for site in TSC.Pager(server.sites):
                
            logger.info('Backing up workbooks and datasources under the {} site changed after {}'.format(site.name, downloadChangesSince))
                
            #logging into the specific site
            tableau_auth1 = TSC.TableauAuth(cfg['tableauServer']['user'], tableauPassword, site_id = site.content_url)
            server.auth.sign_in(tableau_auth1)
            
            sPath = os.path.join(oPath, site.name.translate(remove_punctuation_and_turkish_map))
            if os.path.isdir(sPath) is False:
                os.makedirs(sPath)

            #iterating through each workbook in the specified site to download and extract
            for workbook in TSC.Pager(server.workbooks, req_option):
                
                projectName = workbook.project_name.translate(remove_punctuation_and_turkish_map)
                xPath = os.path.join(sPath, projectName)
                workbookFileName = os.path.join(xPath, workbook.name.translate(remove_punctuation_and_turkish_map)) + '.twb'

                if os.path.isdir(xPath) is False:
                    os.makedirs(xPath)

                file_path = server.workbooks.download(workbook.id, filepath = workbookFileName)
                
                #extractWorkbook(file_path, site.name, projectName, workbook.project_id, workbook.id, os.path.basename(file_path), xPath)

            #iterating through each datasource in the specified site to downlad and extract
            for datasources in TSC.Pager(server.datasources, req_option):
            
                projectName = datasources.project_name.translate(remove_punctuation_and_turkish_map)
                dPath = os.path.join(sPath, projectName)
                datasourceFileName  = os.path.join(dPath, datasources.name.translate(remove_punctuation_and_turkish_map)) + ".tdsx"

                if os.path.isdir(dPath) is False:
                    os.makedirs(dPath)

                file_path = server.datasources.download(datasources.id, filepath = datasourceFileName, include_extract = False)
                extractDatasource(file_path, site.name, projectName, datasources.project_id, datasources.id, os.path.basename(file_path), dPath)
        
        #pushing changes to git and timestamping when this script was run
        if "nothing to commit" not in repo.git.status():
            repo.git.add('.')
            repo.git.commit(m = "last backup: " + currentTime.strftime('%Y-%m-%d %H-%M-%S'))
            repo.git.push('origin')
        
        logger.info('Backup Complete')
        server.auth.sign_out()

    except:
        logging.exception('error')
        pass

#function for extracting workbooks and renaming as: siteName\workbookProjectName_[worbookProjectID]\workbookName_<workbookID>
def extractWorkbook(file_path, site_name, project_name, project_id, workbook_id, workbook_name, oPath):
    if re.match(r'.*\.twbx$', file_path):
        zip_ref = zipfile.ZipFile(file_path,'r')
        for info in zip_ref.infolist():
            if re.match(r'.*\.twb$', info.filename):
                nName = workbook_name.replace('.twbx', '_'+workbook_id+'.twb')
                with open(os.path.abspath(os.path.join(oPath, nName)), 'wb') as f:
                    f.write(zip_ref.read(info))
                zip_ref.close()
                os.remove(file_path)

    elif re.match(r'.*\.twb$', file_path):
        pName = os.path.splitext(file_path)[0] + ('_'+workbook_id+'.twb')
        shutil.move(file_path, u"\\\\?\\" + pName)

#function for extracting datasources and renaming as: siteName\datasourceProjectName_[datasourceID]\datasourceName_<datasourceID>    
def extractDatasource(file_path, site_name, project_name, project_id, datasources_id, datasources_name, oPath):
    if re.match(r'.*\.tdsx$', file_path):
        zip_ref = zipfile.ZipFile(file_path,'r')
        for info in zip_ref.infolist():
            if re.match(r'.*\.tds$', info.filename):

                yName = datasources_name.replace('.tdsx', '.tds')
                with open(os.path.join(oPath, yName), 'wb') as f:
                    f.write(zip_ref.read(info))
                zip_ref.close()
                os.remove(file_path)

    elif re.match(r'.*\.tds$', file_path):

        wName = os.path.splitext(file_path)[0] + '.tds'
        shutil.move(file_path, u"\\\\?\\" + wName)

#getting login credentials from config.ini and command line
def getCreds():
    service_id = 'TableauBackup'

    #get password for tableau server
    if not keyring.get_password(service_id, cfg['tableauServer']['user']):
        keyring.set_password(service_id, cfg['tableauServer']['user'], getpass.getpass('Enter Tableau Server Password For {}: '.format(cfg['tableauServer']['user'])))

    #get password for git
    #!
    '''
    if not keyring.get_password(service_id, cfg['git']['login']):
        keyring.set_password(service_id, cfg['git']['login'], getpass.getpass('Enter Git Password For {}: '.format(cfg['git']['login'])))
    '''

    #update password depending on arguments from commandline
    #!
    '''
    if args.password == 'g':
        keyring.set_password(service_id, cfg['git']['login'], getpass.getpass('Enter New Git Password For {}: '.format(cfg['git']['login'])))
    '''
    if args.password == 't':
        keyring.set_password(service_id, cfg['tableauServer']['user'], getpass.getpass('Enter New Tableau Server Password For {}: '.format(cfg['tableauServer']['user'])))
    elif args.password == 'a':
        keyring.set_password(service_id, cfg['tableauServer']['user'], getpass.getpass('Enter New Tableau Server Password For {}: '.format(cfg['tableauServer']['user'])))
        #keyring.set_password(service_id, cfg['git']['login'], getpass.getpass('Enter New Git Password For {}: '.format(cfg['git']['login'])))

    #return (keyring.get_password(service_id, cfg['tableauServer']['user']), keyring.get_password(service_id, cfg['git']['login']))   
    return keyring.get_password(service_id, cfg['tableauServer']['user'])   

main()
