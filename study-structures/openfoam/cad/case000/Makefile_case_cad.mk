# Makefile copied from ./tools/framework/study-structures/openfoam/cad/case000/Makefile_case_cad.mk

ifneq ("$(wildcard ./special-targets.mk)","")
    include special-targets.mk
endif


jsonfile        = $(shell find . -name 'sofa.cad*.json')
paraviewFile    = $(shell node -p "require('$(jsonfile)').buildSettings.paraview")



#   standard targets 
# =============================================================================

.PHONY: stl
stl: 
	@echo "no automatic stl creation provided"


freecad:
	@echo; echo "*** execute >WRITE MESH< inside freecad to provide stl files in >meshCase< ***" ;echo
	@read -p "press ENTER to continue ..." dummy
	make freecad-gui
	make freecad-stl-push


view:
	if [   -f native/geometry.FCStd ]; then   make freecad-gui              ; fi
	if [ ! -f native/geometry.FCStd ]; then   make frameworkview               ; fi
	make paraview


clean: clean-freecad-output clean-vtk
	find . -empty -type d -delete
	make -C ../../../tools/framework  clean



#   framework handling
# =============================================================================

# clone case to a new case with the next available running number 
clone:
	python3 ../../../tools/framework/scripts/sofa-tasks.py clone



# Basic stl/surface handling
# =============================================================================

# check topology of stl files and write log file
checkSurfaces:
	python3 ../../../tools/framework/openFoam/python/foamCad.py checkSurfaces


# combine all stl files into a single regional stl
combineSTL:
	python3 ../../../tools/framework/openFoam/python/foamCad.py combineSTL


# erase all vtk files
clean-vtk:
	python3 ../../../tools/framework/openFoam/python/foamCad.py cleanVTK



# FreeCAD handling
# =============================================================================

freecad-gui:
	if [ ! -f native/geometry.FCStd ]; then cp ../../../tools/framework/openFoam/dummies/cad/geometry.FCStd  native/geometry.FCStd; fi
	freecad-daily native/geometry.FCStd


freecad-stl-push: 
	@echo "\n*** push freecad stl export to ./stl ***"

	# check for freecad stl file existence
	@if   ls meshCase/constant/triSurface/*.stl  >/dev/null 2>&1;  then  echo "";   else   \
		echo "ERROR: provide stl-files in meshCase/constant/triSurface \n"  ; \
		exit 1 ; \
	fi

	@# delete outdated stl files
	@mkdir -p stl ; 
	@if [ ! `find stl -prune -empty 2>/dev/null` ]          ; then     \
		echo "*** OVERWRITING/DELETING EXISTING stl-files in stl folder ***"      ; \
		ls -lA stl  ; \
		read -p "press ENTER to continue ..." dummy  ; \
	fi
	rm -f  stl/*.stl
	@echo ""

	# move freecad stl export to ./stl
	mv meshCase/constant/triSurface/*  stl 
	@echo "\n    list of moved stl files " 
	@ls -lA stl 
	@echo "" 
	make prune-empty-freecad-export-folders


prune-empty-freecad-export-folders:
	@if [ -d meshCase ] ; then  \
		find meshCase -type d -empty -delete  ; \
	fi
	@if [ -d case ] ; then  \
		find case -type d -empty -delete  ;\
	fi


clean-freecad-output:
	rm -rf meshCase
	rm -rf case
	# rm -f  stl/*



# Paraview
# =============================================================================

# open paraview
frameworkview:
	python3 ../../../tools/framework/openFoam/python/foamCad.py view


# opens paraview with the referenced state file
paraview: 
	@echo "*** loaded data is specified in state file and should be made relative from caseXXX ***"
	paraview --state=$(paraviewFile)  

