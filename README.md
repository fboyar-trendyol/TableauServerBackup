# tableau-server-backup

This is a script for backing up tableau server workbooks and datasources to a git repository

This python script tracks changes in git for all workbooks and datasources 
from each site in the listed tableau server location.

This script queries all sites within the listed tableau server and downloads 
workbooks and datasources and then pushes the changes to a apecified git 
repository. 

This script will track changes for any files updated in the time period specified by the user from
when this script is run.

Runs in python3

Dependencies 
- tableauserverclient
- gitpython
- keyring

Instructions:
1) Install and configure Git. Add your ssh key as Access Key to git repository.
2) Set up git repo for backing up workbooks and datasources
3) Clone/download this project and open command line and navigate to this directory where this project is cloned/downloaded
4) Open congif.ini file and input login and URL to Tableau Server and git:  
    [tableauServer]   
    url =  this is the full url to the Tableau Server i.e., https://<i></i>tableau-server-url.com  
    user =  enter the username to login with  
    utc_value = enter the local utc value if server doesn't  contain.

    [git]  
    url = this is the full url to the git repo you created i.e., https://<span></span>gitlab.com/tableau-version-contol  
    projectName = name of the directory where the backup will be stored locally, can match the git project name i.e., tableau-version-control  
    id_rsa = Your server's id_rsa.pub path for login to Stash

   You will be asked password upon command line
5) Install dependencies by running:  
    ```$ pip install -r requirements.txt``` or ```$ sh create_environment.sh``` to create new conda environment.
6) Run this file:  
    ```$ python tableauBackup.py [-p {a,t,g}] (-i <hours> | -f)``` 

   ```$ python tableauBackup.py -p {a|g|p}```  is for changing/updating passwords by:  
   ```-p a``` for all passwords  
   ```-p g``` for git password.  `This option is removed, because we use id_rsa key as Access Key to login on stash.` \
   ```-p t``` for tableau server password  

   ```$ python tableauBackup.py (-i <hours> | -f)``` is for specifying the type of backup  
   ```-i <hours>``` for setting the time period to scan for changes, default is 1 so it will scan for changes made in the last hour  
   ```-f``` for full load that will back up everything regardless  

   Multiple arguments is valid as well:  
   ```$ python tableauBackup.py -p a -i 3```

   You can type ```$python tableauBackup.py --help``` for more information