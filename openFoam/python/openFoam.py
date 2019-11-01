#!/usr/bin/env python3

#--------------------------------------------------------------------------#
# Contributor: Sebastian Tueck, Jan Lehmkuhl                               #
# Last Change: February 01 2019                                            #
# Topic:       Project builder                                             #
#--------------------------------------------------------------------------#

# import librarys
import json
import os
import sys
import shutil
import fnmatch
import subprocess

from fileHandling import createDirSafely
from fileHandling import createSymlinkSavely
from fileHandling import copyFileSafely
from fileHandling import copyFolderSafely
from fileHandling import loadJson

def findFile(fileName, turnFolder):
    # traverses a tree upwards till it finds turnfolder and then dives into
    # turnfolder till it finds file
    #
    # Args:
    #   fileName:   s: name of the file that is searched for
    #   turnfolder: s: name of the folder to turn on
    #
    # Return:
    #   path:       s: relative path to the file
    #
    i = 0
    wd = os.getcwd()
    subdirs = os.listdir(os.getcwd())
    while i < 5:
        if turnFolder in subdirs:
            for root, dirs, files in os.walk(os.path.join(wd, turnFolder)):
                if fileName in files:
                    path = os.path.relpath(
                        os.path.join(root, fileName), os.getcwd())
                    return(path)
            else:
                print("Could not find file >%s< in >%s<" %
                      (fileName, os.path.join(wd, turnFolder)))
                return(False)
        wd = os.path.join(wd, os.path.pardir)
        subdirs = os.listdir(wd)
        i += 1
    else:
        print("Could not find folder >%s<" % turnFolder)
        return(False)


def findFolder(folderName, turnFolder):
    # traverses a tree upwards till it finds turnfolder and then dives into
    # turnfolder till it finds folder
    #
    # Args:
    #   folderName: s: name of the folder that is searched for
    #   turnfolder: s: name of the folder to turn on
    #
    # Return:
    #   path:       s: relative path to the file
    #
    i = 0
    wd = os.getcwd()
    subdirs = os.listdir(os.getcwd())
    while i < 5:
        if turnFolder in subdirs:
            for root, dirs, files in os.walk(os.path.join(wd, turnFolder)):
                if folderName in dirs:
                    path = os.path.relpath(
                        os.path.join(root, folderName), os.getcwd())
                    return(path)
            else:
                print("Could not find folder >%s< in >%s<" %
                      (folderName, os.path.join(wd, turnFolder)))
                return(False)
        wd = os.path.join(wd, os.path.pardir)
        subdirs = os.listdir(wd)
        i += 1
    else:
        print("Could not find folder >%s<" % turnFolder)
        return(False)


def cfdAspectSelector(path=None):
    # determines the aspectType of the case from the name of the containing folder
    #
    # Args:
    #   path:       s: path to pass
    #
    # Return:
    #   aspectName:  s: Name of the containing folder stripped of numbers
    #               this should equal the aspectType
    #
    if path is None:
        path = "./"
        caseFolder = os.path.basename(os.getcwd())
    else:
        caseFolder = os.path.basename(path)
    aspectName = ''.join(
        [i for i in caseFolder if not i.isdigit()])  # remove digits
    if aspectName in foamStructure:
        if aspectName == "cad":
            return(CadCase(path))
        elif aspectName == "mesh":
            return(MeshCase(path))
        elif aspectName == "run":
            return(RunCase(path))
        elif aspectName == "survey":
            return(SurveyCase(path))
    else:
        print("Unknown aspect >%s<" % aspectName)
        return(False)

class Aspect(object):
    # base class to handle all operations related to an aspects

    global foamStructure

    def __init__(self, aspectType, path="./"):
        self.aspectType = aspectType
        self.path = path
        self.name = "Aspect"

    def create(self):
        # creates an aspect of self.aspectType at location self.path
        # according to the entrys in the global dictionary foamStructure
        #
        # Args:
        #
        # Return:
        #   side effects: creates Aspect
        #
        aspectName = foamStructure[self.aspectType]["aspectName"]
        createDirSafely(os.path.join(self.path, aspectName))
        makefilePath = findFile("Makefile_aspect.mk", "tools")
        if makefilePath:  # if find file fails it returns false
            #copyFileSafely(makefilePath, os.path.join(self.path, aspectName, "Makefile"))
            createSymlinkSavely(    makefilePath,       # aspect Makefile
                                    os.path.join( self.path, aspectName, "Makefile") )
            if self.aspectType == "mesh":
                meshOvPath  = findFile("MeshOverview.Rmd", "tools")
                meshRepPath = findFile("MeshReport.Rmd"  , "tools")
                createDirSafely(os.path.join(self.path, aspectName, "doc/template01"))
                if meshOvPath:
                    copyFileSafely(meshRepPath, os.path.join(self.path, aspectName, "doc/template01/meshReport.Rmd"))
                    copyFileSafely(meshOvPath,  os.path.join(self.path, aspectName, "doc/meshOverview.Rmd"))
            if self.aspectType == "run":
                createDirSafely(os.path.join(self.path, aspectName, "doc/template01"))
                runOvPath = findFile("RunOverview.Rmd", "tools")
                if runOvPath:
                    copyFileSafely(runOvPath, os.path.join(self.path, aspectName, "doc/StudyOverview.Rmd"))
            case = cfdAspectSelector(os.path.join(self.path, aspectName))
            case.create()

class Case(object):
    # base class to handle all operations related to cases

    global foamStructure

    def __init__(self, aspectType=None, path="./"):
        # name of class
        self.name = "Case"
        # aspectType of class, e.g. cad, mesh ....
        self.aspectType = aspectType
        # relative path to Aspect
        self.path = path
        # name of current case
        self.caseName = os.path.basename(os.path.abspath(self.path))
        # initialize variables 
        self.caseJson = None
        self.linkedCase = None
        self.linkedReport = None
        self.pathToLinkedCase = None
        self.pathToLinkedReport = None
        self.symlinksClean = False
        # check if case .json exists
        if os.path.exists(os.path.join(self.path, self.aspectType + ".json")):
            # load case .json 
            self.caseJson = loadJson(os.path.join(self.path, self.aspectType + ".json"))
            # extract linked cases from case.json according to foamStructure gen in project.json
            self.linkedCase = self.caseJson["buildSettings"][foamStructure[self.aspectType]["linkName"]]
            if self.linkedCase:
                # differentiate between single links and a list of links (survey)
                if isinstance(self.linkedCase, str):
                    self.pathToLinkedCase = findFolder(
                        self.linkedCase, foamStructure[foamStructure[self.aspectType]["linkType"]]["aspectName"])
                elif isinstance(self.linkedCase, list):
                    self.pathToLinkedCase = []
                    for element in self.linkedCase:
                        self.pathToLinkedCase.append(findFolder(
                            element, foamStructure[foamStructure[self.aspectType]["linkType"]]["aspectName"]))
                else:
                    print(
                        "Unexpected aspectType of self.linkPath in __init__ of %s" % self.name)
            self.linkedReport = self.caseJson["buildSettings"]["report"]
            if self.linkedReport: 
                print( os.getcwd() )
                # differentiate between single links and a list of links (survey)
                self.pathToLinkedReport = "../doc/" +self.linkedReport
                createDirSafely( self.pathToLinkedReport ) 
                createSymlinkSavely( self.pathToLinkedReport, "postTemplate" )


    def nextCaseName(self, path="./"):
        # finds the next case name in a series of folder of type xxx123
        #
        # Args:
        #   path:   path to folder to look in
        #
        # Return:
        #   name:   name of the next case folder
        #
        subfolders = [f.name for f in os.scandir(path) if f.is_dir()]
        maxNo = 0
        charCount = len(self.aspectType)
        for folder in subfolders:
            if folder[:charCount] == self.aspectType:
                currentNo = int(folder[charCount:])
                if currentNo > maxNo:
                    maxNo = currentNo
        CaseName = str(self.aspectType + format(maxNo + 1, "0>3d"))
        return(CaseName)

    def getStudyName(self):
        # finds the projectname of a case
        #
        # Args:
        #
        # Return:
        #   name:   name of the next case folder
        #
        i = 0
        wd = os.getcwd()
        subdirs = os.listdir(os.getcwd())
        while i < 5:
            if foamStructure["cad"]["aspectName"] in subdirs:
                return(os.path.basename(os.path.normpath(wd)))
            else:
                wd = os.path.join(wd, os.path.pardir)
                subdirs = os.listdir(wd)
                i += 1
        else:
            print("Could not find project name")
            return(False)

    def create(self):
        # create a new case inside a Aspect depending on the aspectType of case
        #
        # Args:
        #
        # Return:
        #   side effects
        #
        jsonPath = findFile(self.aspectType + ".json", "tools")
        makePath = findFile(str("Makefile_case_" + self.aspectType + ".mk"), "tools")
        gitignorePath = findFile(".gitignore_foam", "tools")
        caseName = self.nextCaseName()
        if (jsonPath and makePath):
            createDirSafely(os.path.join(self.path, caseName))
            ### Makefile
            #copyFileSafely(makePath, os.path.join(self.path, caseName, "Makefile"))
            createSymlinkSavely(makePath, os.path.join(
                self.path, caseName, "Makefile"))
            ### json
            copyFileSafely(jsonPath, os.path.join(
                self.path, caseName, self.aspectType + ".json"))
            createSymlinkSavely(gitignorePath, os.path.join(
                self.path, caseName, ".gitignore"))
        return(True)

    def clone(self):
        # create a clone of the current case
        #
        # Args:
        #
        # Return:
        #   side effects: makes a clone of the case
        #
        currentCase = os.path.basename(os.getcwd())
        caseName = self.nextCaseName(os.pardir)
        path = os.path.join(os.pardir, caseName)
        while True:
            print("Clone case from >%s< to >%s< ? (y/n)" %
                  (currentCase, caseName))
            answer = input().lower()
            if answer in ["y", "yes"]:
                while True:
                    print("Include results? (y/n)")
                    answer2 = input().lower()
                    if answer2 in ["y", "yes"]:
                        print("Cloning complete case >%s< to >%s<" % (currentCase, caseName))
                        shutil.copytree(os.path.join(os.pardir, currentCase),
                                        path, symlinks=True)
                        break
                    if answer2 in ["n", "no"]:
                        print("Cloning case >%s< to >%s< without results" % (currentCase, caseName))
                        os.makedirs(os.path.join(os.pardir, caseName))
                        for name in os.listdir("."):
                            if fnmatch.fnmatch(name, "[1-9]*") or fnmatch.fnmatch(name, "[0-9].[0-9]*"):
                                continue
                            elif fnmatch.fnmatch(name, "processor*"):
                                createDirSafely(os.path.join(path,name))
                                for subDir in os.listdir(os.path.join("./", name)):
                                    if fnmatch.fnmatch(subDir, "[1-9]*") or fnmatch.fnmatch(subDir, "[0-9].[0-9]*"):
                                        continue
                                    else:
                                        copyFolderSafely(os.path.join(name, subDir), os.path.join(path,name,subDir))
                                continue
                            elif fnmatch.fnmatch(name, "postProcessing*"):
                                continue
                            elif fnmatch.fnmatch(name, "log*"):
                                continue
                            elif os.path.isfile(name):
                                copyFileSafely(name,os.path.join(path,name))
                                continue
                            else:
                                copyFolderSafely(name,os.path.join(path,name))
                        break
                while True:
                    print("\nCommit cloning of >%s< to >%s< ? (y/n)" %
                            (currentCase, caseName))
                    answer3 = input().lower()
                    if answer3 in ["y", "yes"]:
                        studyName = self.getStudyName()
                        os.system('git add %s' % path)
                        os.system('git commit -m "[%s%s] #CLONE \'cloning case >%s< to >%s<\'"' % (
                            studyName, caseName.capitalize(), currentCase, caseName))
                        break
                    elif answer3 in ["n", "no"]:
                        break
                break
            if answer in ["n", "no"]:
                break

    def clear(self):
        # removes all files, folders and symlinks from a case, but spares
        # out the Makefile and the .json file of the case
        #
        # Args:
        #
        # Return:
        #   side effects: removes folders
        #
        caseName = os.path.basename(os.getcwd())
        while True:
            print("Do you really want to clear case >%s< ? (y/n)" % caseName)
            answer = input()
            answer = answer.lower()
            if answer in ["y", "yes"]:
                for root, dirs, files in os.walk("./", topdown=False):
                    for name in files:
                        if name == "Makefile":
                            continue
                        if name == ".gitignore":
                            continue
                        elif name.endswith("json"):
                            continue
                        else:
                            os.remove(os.path.join(root, name))
                            print("Removing file >%s< from case" %
                                  os.path.join(root, name))
                    for name in dirs:
                        if os.path.islink(os.path.join(root, name)):
                            os.remove(os.path.join(root, name))
                            print("Removing link >%s<" %
                                  os.path.join(root, name))
                        else:
                            os.rmdir(os.path.join(root, name))
                            print("Removing folder >%s< from case" %
                                  os.path.join(root, name))
                while True:
                    print("Commit clearing of %s ? (y/n)" % caseName)
                    answer = input()
                    answer = answer.lower()
                    if answer in ["y", "yes"]:
                        studyName = self.getStudyName()
                        os.system('git add .')
                        os.system('git commit -m "[%s%s] #CLEAR \'cleared case >%s< in project >%s<\'"' 
                                  % (studyName, caseName.capitalize(), caseName, studyName))
                        break
                    elif answer in ["n", "no"]:
                        break
                break
            elif answer in ["n", "no"]:
                break

    def makeMainSymlink(self):
        # links the folder stated in the case json into the directory
        #
        # Args:
        #
        # Return:
        #   side effects:  creates the main symlink
        #
        # make sure symlinks are clean but avoid double calling
        if not self.symlinksClean:
            self.removeSymlinks
        # check if a file to link to has been specified in *.json file
        if self.linkedCase:
            # check if the file to link to exists
            if self.pathToLinkedCase:
                #os.symlink(self.pathToLinkedCase, self.linkedCase)
                createSymlinkSavely(self.pathToLinkedCase, self.linkedCase)
                #print("Create link to >%s<" % self.pathToLinkedCase)
                return(True)
        else:
            print("No link specified for this case yet")
            return(False)

    def removeSymlinks(self):
        # removes the symlinks from a case which have been created
        # by the script
        #
        # Args:
        #
        # Result:
        #   side effects : removes symlinks
        #
        # Lists of folders and extensions to delete
        extensions = [".stl", ".vtk"]
        folder = ["polyMesh", "cadPics", "meshPics",
                  "drafts", "meshReport", "layerSizing"]
        for key in foamStructure:
            folder.append(key)
        # Traverse all subdirectories in case
        for root, dirs, files in os.walk("./"):
            for dirName in dirs:
                if os.path.islink(os.path.join(root, dirName)):
                    # remove digits from foldernames to compare with folder
                    stripped = ''.join([i for i in dirName if not i.isdigit()])
                    if stripped in folder:
                        os.remove(os.path.join(root, dirName))
                        print("Removing link >%s<" %
                              os.path.join(root, dirName))
            for fileName in files:
                if os.path.islink(os.path.join(root, fileName)):
                    # check if file extension is in extensions
                    if os.path.splitext(os.path.join(root, fileName))[1] in extensions:
                        os.remove(os.path.join(root, fileName))
                        print("Removing link >%s<" %
                              os.path.join(root, fileName))
        self.symlinksClean = True

    def copyReport(self, run = False):
        # method to copy reports either from the template directory or
        # reporting
        #
        # Args:
        #
        # Return:
        #   side effects: creates symlinks for mesh
        #
        if self.aspectType == "cad" :
            print("Reports are not supported for >cad<")
            exit(0)
        elif self.aspectType == "survey" :
            print("Reports are not yet supported for >cad<")
            exit(0)
        reportSrc = ""
        reportTemplate = self.caseJson["buildSettings"]["report"]
        if reportTemplate in  os.listdir(os.path.join(self.path, "../doc")):
            reportPath = os.path.join(self.path, "../doc", reportTemplate)
            for file in os.listdir(reportPath):
                if fnmatch.fnmatch(file, '*.Rmd'):
                    if self.aspectType == "mesh" :
                        reportSrc = os.path.join(reportPath, file)
                        reportDst = os.path.join(self.path, "doc/meshReport/meshReport.Rmd")
                    elif self.aspectType == "run" :
                        reportSrc = os.path.join(reportPath, file)
                        reportDst = os.path.join(self.path, "doc/runReport/runReport.Rmd")
                else: 
                    print("Unabel to find a report in >%s" %reportPath)
                    exit(0)
        else:
            print("Unabel to find >%s in")
            exit(0)
        if not reportSrc :
            if self.aspectType == "mesh" :
                reportSrc = findFile("MeshReport.Rmd", "tools")
                reportDst = os.path.join(self.path, "doc/meshReport/meshReport.Rmd")
            if self.aspectType == "run" :
                reportSrc = findFile("RunReport.Rmd", "tools")
                reportDst = os.path.join(self.path, "doc/runReport/runReport.Rmd")
        print("Updating report in >%s" %self.caseName)
        if not os.path.exists(os.path.dirname(reportDst)):
            createDirSafely(os.path.dirname(reportDst))
        if os.path.exists(reportDst):
            print("Deleting > %s" %reportDst)
            os.remove(reportDst)
        copyFileSafely(src = reportSrc, dst = reportDst)  
        if run:
            cmd = ['R', '-e' , 'rmarkdown::render(\'' + reportDst + '\')']
            #logFilePath = os.path.join("log",str("runReport" + ".log"))
            runReport = subprocess.Popen(cmd)# , logFilePath)  
            runReport.wait()    


    def commitInit(self):
        # asks user if he wants to commit the initialisation to git
        #
        # Args:
        #
        # Result:
        #   side effects:   commits changes of case
        #
        studyName = self.getStudyName()
        caseName = os.path.basename(os.getcwd())
        while True:
            print("Commit initialisation of %s ? (y/n)" % caseName)
            answer = input()
            answer = answer.lower()
            if answer in ["y", "yes"]:
                studyName = self.getStudyName()
                os.system('git add .')
                os.system('git commit -m "[%s%s] #INIT \'initialised case >%s< in project >%s<\'"' % (
                    studyName, caseName.capitalize(), caseName, studyName))
                break
            elif answer in ["n", "no"]:
                break

    def commitChanges(self):
        # asks user if he wants to commit changes to case
        #
        # Args:
        #
        # Result:
        #   side effects:   commits changes of case
        #
        caseName = os.path.basename(os.getcwd())
        while True:
            print("Commit changes in %s ? (y/n)" % caseName)
            answer = input()
            answer = answer.lower()
            if answer in ["y", "yes"]:
                while True:
                    print("Please enter a commit message:")
                    message = input()
                    if not message == "":
                        break
                studyName = self.getStudyName()
                os.system('git add .')
                os.system('git commit -m "[%s%s] #CHANGE \'%s\'"' %
                          (studyName, caseName.capitalize(), message))
                break
            elif answer in ["n", "no"]:
                break

    def updateJson(self):
        # update json file of a case with newest version from tools
        #
        # Args:
        #
        # Result:
        #   side effects:   overwrite current .json
        #

        # find and load most recent version of json from framework
        newJsonPath = findFile(self.aspectType + ".json", "tools")
        newJson = loadJson(newJsonPath)
        # check if present
        if newJsonPath:
            # loop first level of keys 
            for key1 in self.caseJson:
                # if found element is a string assign value
                if isinstance(self.caseJson[key1], str):
                    newJson[key1] = self.caseJson[key1]
                # if found element is a dict iterate
                elif isinstance(self.caseJson[key1], dict):
                    # assign value 
                    for key2 in self.caseJson[key1]:
                        newJson[key1][key2] = self.caseJson[key1][key2]
        else:
            print("No version of %s found in framework" %str(self.aspectType + ".json"))
        # save new Json file over old file
        with open(os.path.join(self.path, self.aspectType + ".json"), 'w') as outfile:
            json.dump(newJson, outfile, indent=4)


class CadCase(Case):
    # Specialized class for cad cases, which inherits from the base Case class

    def __init__(self, path="./"):
        super().__init__("cad", path)
        self.name = "CadCase"

    def create(self):
        # specialized method which creates all folders needed in
        # a case of aspectType cad
        #
        # Args:
        #
        # Return:
        #   side effects: creates directories
        #
        caseName = self.nextCaseName()
        createDirSafely(os.path.join(self.path, caseName, "native"))
        createDirSafely(os.path.join(self.path, caseName, "stl"))
        createDirSafely(os.path.join(self.path, caseName, "vtk"))
        createDirSafely(os.path.join(self.path, caseName, "doc/drafts"))
        createDirSafely(os.path.join(self.path, caseName, "doc/cadPics"))
        makePath =      findFile( "Makefile_case_cad.mk",   "tools")
        gitignorePath = findFile( ".gitignore_cad",         "tools")
        if makePath:
            createSymlinkSavely(    makePath, 
                                    os.path.join( self.path, caseName, "Makefile"))
        if gitignorePath:
            createSymlinkSavely( gitignorePath, 
                                 os.path.join( self.path, caseName, ".gitignore"))

    def initCase(self):
        if len(os.listdir(".")) <= 1:
            createDirSafely("native")
            createDirSafely("stl")
            createDirSafely("vtk")
            createDirSafely("doc/drafts")
            createDirSafely("doc/cadPics")
            makePath =      findFile( "Makefile_case_cad.mk",   "tools")
            gitignorePath = findFile( ".gitignore_cad",         "tools")
            if makePath:
                copyFileSafely( makePath,       "Makefile")
            if gitignorePath:
                copyFileSafely( gitignorePath,  ".gitignore")
            self.commitInit()
        else:
            print("Case is already initialised. Please run >make clean< first")

    def makeSymlinks(self):
        print("Cases of aspectType >cad< do not support option symlinks")


class MeshCase(Case):
     # Specialized class for cad cases, which inherits from the base Case class

    def __init__(self, path="./"):
        super().__init__("mesh", path)
        self.name = "MeshCase"
        self.Builder = foamBuilder()

    def makeSymlinks(self):
        # specialized method to create all symlinks needed for a case
        # of aspectType mesh
        #
        # Args:
        #
        # Return:
        #   side effects: creates symlinks for mesh
        #
        linkedGeometry = False
        # if symlinks already exist, delete them
        self.removeSymlinks()
        if self.makeMainSymlink():
            createDirSafely("constant/triSurface")
            createDirSafely("doc")
            createDirSafely( self.pathToLinkedCase+ "/doc")
            createDirSafely( self.pathToLinkedCase+ "/stl")
            createDirSafely( self.pathToLinkedCase+ "/vtk")
            for extension in ["stl", "vtk"]:
                for element in os.listdir(os.path.join(self.pathToLinkedCase, extension)):
                    if element.endswith("." + extension):
                        createSymlinkSavely(os.path.join(self.pathToLinkedCase, extension, element), os.path.join(
                            "./constant/triSurface/", element))
                        if element.endswith(".stl"):
                            linkedGeometry = True
            for element in os.listdir(os.path.join(self.pathToLinkedCase, "doc")):
                createSymlinkSavely(os.path.join(
                    self.pathToLinkedCase, "doc", element), os.path.join("./doc", element))
            if not linkedGeometry:
                print("WARNING: Did not link to any geometry files")
            return(True)

    def initCase(self):
        # specialised method to initialise a case of aspectType mesh
        #
        # Args:
        #
        # Returns:
        #   side effects: creates directories, copies files makes symlinks
        #
        if os.path.isdir("./system"):
            print(
                "Case is already initialized. If you want to reinitialize please delete >system")
        elif self.makeSymlinks():
            meshReportPath = findFile("MeshReport.Rmd", "tools")
            layerSizingPath = findFile("LayerSizing.Rmd", "tools")
            #meshStatePath = findFile("mesh.pvsm", "tools")
            if (meshReportPath and layerSizingPath ): # and meshStatePath):
                self.Builder.makeMesh()
                createDirSafely("doc/meshReport")
                createDirSafely("doc/layerSizing")
                createDirSafely("doc/meshPics")
                open("paraview.foam", "a").close()
                self.copyReport()
                #copyFileSafely(meshReportPath, "doc/meshReport/meshReport.Rmd")
                copyFileSafely(layerSizingPath,"doc/layerSizing/layerSizing.Rmd")
                #copyFileSafely(meshStatePath, "mesh.pvsm")
                self.commitInit()

class RunCase(Case):
    # Class for run cases

    def __init__(self, path=None):
        super().__init__("run", path)
        self.name = "RunCase"
        if self.caseJson:
            self.Builder = foamBuilder(self.caseJson["buildSettings"])

    def makeSymlinks(self):
        # specialized method to create all symlinks needed for a case
        # of aspectType run
        #
        # Args:
        #
        # Return:
        #   side effects: creates symlinks for run
        #
        self.removeSymlinks()
        if self.makeMainSymlink():
            createDirSafely("constant")
            createDirSafely("doc")
            createSymlinkSavely(os.path.join(
                self.pathToLinkedCase, "constant/polyMesh"), os.path.join("./constant/polyMesh"))
            createDirSafely( self.pathToLinkedCase+ "/doc")
            for element in os.listdir(os.path.join(self.pathToLinkedCase, "doc")):
                currentPath = os.path.join(
                    self.pathToLinkedCase, "doc", element)
                createSymlinkSavely(currentPath, os.path.join("doc", element))
            return(True)

    def initCase(self):
        # specialised method to initialise a case of aspectType run
        #
        # Args:
        #
        # Returns:
        #   side effects: creates directories, copies files makes symlinks
        #
        if os.path.isdir("./system"):
            print(
                "Case is already initialized. If you want to reinitialize please delete >system")
        elif self.makeSymlinks():
            self.Builder.makeBase()
            self.Builder.makeTurbulence()
            self.Builder.makeDynamicMesh()
            self.Builder.makePorousZone()
            self.commitInit()

class SurveyCase(Case):
    # Class for survey cases

    def __init__(self, path=None):
        super().__init__("survey", path)
        self.name = "surveyCase"

    def makeSymlinks(self):
        # specialized method to create all symlinks needed for a case
        # of type run
        #
        # Args:
        #
        # Return:
        #   side effects: creates symlinks for run
        #
        self.removeSymlinks()
        if False in self.pathToLinkedCase:
            return(False)
        for element in self.pathToLinkedCase:
            createSymlinkSavely(element, os.path.basename(element))


class foamBuilder(object):
    # class to handle the setup of openFoam folder structures from the
    # foamFiles.json file

    def __init__(self, foamCaseSettings=None):
        self.foamJson = loadJson(findFile("foamFiles.json", "tools"))
        self.setupPath = findFolder("openFoam-setup", "tools")
        self.foamCaseSettings = foamCaseSettings

    def makeMesh(self):
        # reads the file structure from foamFiles.json and copies all nessesary files
        # listed there to create a mesh
        #
        # Args:
        #
        # Return:
        #   side effects: builds an OpenFOAM structure for meshes
        #
        if self.foamJson:
            if self.setupPath:
                meshStruct = self.foamJson["mesh"]
                for folder in meshStruct:
                    createDirSafely(folder)
                    for file in meshStruct[folder]:
                        copyFileSafely(os.path.join(
                            self.setupPath + meshStruct[folder][file]), os.path.join(folder, file))

    def makeBase(self):
        # reads the file structure from foamFiles.json and copies all nessesary files
        # listed there to create the basic structure for a solver given in
        # the run.json file
        #
        # Args:
        #
        # Return:
        #   side effects: builds an OpenFOAM structure for meshes
        #
        if self.foamJson:
            if self.setupPath:
                solver = self.foamCaseSettings["solver"]
                if solver in self.foamJson:
                    baseStruct = self.foamJson[solver]
                    for folder in baseStruct:
                        createDirSafely(folder)
                        for file in baseStruct[folder]:
                            copyFileSafely(os.path.join(
                                self.setupPath + baseStruct[folder][file]), os.path.join(folder, file))
                else:
                    print("Unknown Solver >%s< specified in run.json" % solver)

    def makeTurbulence(self):
        # reads the file structure from foamFiles.json and copies all nessesary files
        # listed there to add the nessessary files for a turbulence model given in
        # the run.json file
        #
        # Args:
        #
        # Return:
        #   side effects: adds turbulence files
        #
        if self.foamJson:
            if self.setupPath:
                turbulenceModell = self.foamCaseSettings["turbulenceModel"]
                if turbulenceModell in self.foamJson["turbulence"]:
                    baseStruct = self.foamJson["turbulence"][turbulenceModell]
                    for folder in baseStruct:
                        createDirSafely(folder)
                        for file in baseStruct[folder]:
                            copyFileSafely(os.path.join(
                                self.setupPath + baseStruct[folder][file]), os.path.join(folder, file))
                else:
                    print("Unknown turbulence model >%s< specified in run.json" %
                          turbulenceModell)

    def makePorousZone(self):
        # reads the file structure from foamFiles.json and copies all nessesary files
        # listed there to add the nessessary files for a porous zone as given in
        # the run.json file
        #
        # Args:
        #
        # Return:
        #   side effects: adds porous zone
        #
        if self.foamJson:
            if self.setupPath:
                porousZone = self.foamCaseSettings["porousZone"]
                if porousZone.lower() in ["true", "yes"]:
                    baseStruct = self.foamJson["porousZone"]
                    for folder in baseStruct:
                        createDirSafely(folder)
                        for file in baseStruct[folder]:
                            copyFileSafely(os.path.join(
                                self.setupPath + baseStruct[folder][file]), os.path.join(folder, file))

    def makeDynamicMesh(self):
        # reads the file structure from foamFiles.json and copies all nessesary files
        # listed there to add the nessessary files for a porous zone as given in
        # the run.json file
        #
        # Args:
        #
        # Return:
        #   side effects: adds porous zone
        #
        if self.foamJson:
            if self.setupPath:
                dynamicMesh = self.foamCaseSettings["dynamicMesh"]
                if dynamicMesh.lower() in ["true", "yes"]:
                    baseStruct = self.foamJson["dynamicMesh"]
                    for folder in baseStruct:
                        createDirSafely(folder)
                        for file in baseStruct[folder]:
                            copyFileSafely(os.path.join(
                                self.setupPath + baseStruct[folder][file]), os.path.join(folder, file))


###############################################################################
# MAIN PROGRAMM
###############################################################################

# read entryPoint from command input options
if len(sys.argv) >= 2:
    entryPoint = sys.argv[1]
else: 
    print("ERROR: no entryPoint is specified for openFoam.py")
    sys.exit(0)
    entryPoint = 'defaultEntryPointForDebugging'
    print("*** starting openFoam.py with hard coded entryPoint: >" + entryPoint + "< for debugging purpose ***" )
    print("better use launch.json in VS Code to specifiy settings") 
print("starting openFoam.py with arg: >" + entryPoint + "< in: " + os.getcwd() )


# find project.json 
i = 0
wd = os.getcwd()
subdirs = os.listdir(os.getcwd())
while i < 4:
    if "project.json" in subdirs:
        projectJsonPath = os.path.join(wd, "project.json" )
        projectJson = loadJson(projectJsonPath)
        foamStructure = projectJson["foamStructure"]
        break
    else:
        wd = os.path.join(wd, os.path.pardir)
        subdirs = os.listdir(wd)
        i += 1
else:
    print("Could not find project.json")
    sys.exit(0)

if entryPoint == "initFoam":
    projectStruct = loadJson('project.json')
    for studyFolder in projectStruct['foamFolders']:
        if not os.path.exists(studyFolder):
            print("creating study >" +studyFolder +"< and the interior")
            for element in foamStructure:
                newAspect = Aspect(element, studyFolder)
                newAspect.create()
            copyFileSafely( findFile(    "study-documentation.md", "tools") 
                          , studyFolder+ "/README-study.md" )
            while True:
                print("Commit creation of study %s ? (y/n)" % studyFolder)
                answer = input()
                answer = answer.lower()
                if answer in ["y", "yes"]:
                    os.system('git add .')
                    os.system('git commit -m "[%s] #INIT \'created study %s\'"' % (studyFolder, studyFolder))
                    break
                elif answer in ["n", "no"]:
                    break           
        else:
            print("skipping study >" + studyFolder + " since it already exists")

elif entryPoint == "newCase":
    currentCase = cfdAspectSelector()
    currentCase.create()

elif entryPoint == "initCase":
    currentCase = cfdAspectSelector()
    currentCase.initCase()

elif entryPoint == "symlinks":
    currentCase = cfdAspectSelector()
    currentCase.makeSymlinks()

elif entryPoint == "clone":
    currentCase = cfdAspectSelector()
    currentCase.clone()

elif entryPoint == "clear":
    currentCase = cfdAspectSelector()
    currentCase.clear()

elif entryPoint == "commit":
    currentCase = Case("run")
    currentCase.commitChanges()

elif entryPoint == "overview":
    createDirSafely("doc")
    files = os.listdir("doc")
    for fileName in files:
        if fnmatch.fnmatch(fileName, "*verview*.Rmd"):
            os.system('R -e "rmarkdown::render(\'doc/' + fileName + '\')"')
            break
    else:
        print("Unabel to find RMarkdown file")

elif entryPoint == "updateAllReports":
    while True:
        print("Run reports after updating ? (y/n)")
        answer = input()
        answer = answer.lower()
        if answer in ["y", "yes"]:
            runReports = True
            break
        elif answer in ["n", "no"]:
            runReports = False
            break
    for folder in sorted(os.listdir(".")):
        aspectName = ''.join([i for i in folder if not i.isdigit()])  # remove digits
        if aspectName in foamStructure:
            currentCase = cfdAspectSelector(os.path.join("./", folder))
            currentCase.copyReport(runReports)
    if runReports:
        if not os.path.exists("doc"):
            print("Directory >doc< doesn't exist in: " + os.getcwd() )
            exit(0)
        files = os.listdir("doc")
        for fileName in files:
            if fnmatch.fnmatch(fileName, "*verview*.Rmd"):
                os.system('R -e "rmarkdown::render(\'doc/' + fileName + '\')"')
                break
        else:
            print("Unabel to find RMarkdown file")

elif entryPoint == "updateReport":
    while True:
        print("Run reports after updating ? (y/n)")
        answer = input()
        answer = answer.lower()
        if answer in ["y", "yes"]:
            runReports = True
            break
        elif answer in ["n", "no"]:
            runReports = False
            break
    currentCase = cfdAspectSelector()
    currentCase.copyReport(runReports)

elif entryPoint == "updateJson":
    for folder in sorted(os.listdir(".")):
        aspectName = ''.join([i for i in folder if not i.isdigit()])  # remove digits
        if aspectName in foamStructure:
            print("Updating .json in >%s" %folder)
            currentCase = cfdAspectSelector(os.path.join("./", folder))
            currentCase.updateJson()

elif entryPoint == "test":
    print("Nothing defined")
            