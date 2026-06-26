##########################################################################
# ADOBE CONFIDENTIAL
# ___________________
#  Copyright 2010-2023 Adobe
#  All Rights Reserved.
# * NOTICE:  Adobe permits you to use, modify, and distribute this file in
# accordance with the terms of the Adobe license agreement accompanying it.
# If you have received this file from a source other than Adobe,
# then your use, modification, or distribution of it requires the prior
# written permission of Adobe.
##########################################################################

from .custom_graph import *

def initializeSDPlugin():
    CustomGraph.init()

def uninitializeSDPlugin():
    CustomGraph.uninit()
