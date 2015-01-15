# -*- coding: utf-8 -*-
"""
Represents a tree of worker and manager processes for efficient parallel computing
on distributed systems.  Is most useful when a large number of workers are required
and when the amount of data that needs to be sent to them is large. In this case,
a hierarchy of managers can all send data to their children workers at the same time.

Created on Wed Jan 14 13:08:19 2015

@author: Brian Donovan briandonovan100@gmail.com
"""

from mpi4py import MPI


# Represents a hierarchy of worker and manager processes.  This facilitates fast dissemination of
# data to workers for efficient parallel computations
class ProcessTree:
    
    # Simple constructor.  Should be called by ALL MPI Processes
    # Params:
        # branching_factor - Max number of children each manager should have
        # height - The height of the tree
        # desired_leaves - should be less than branching_factor^height
    def __init__(self, branching_factor, height, desired_leaves):
        self.branching_factor = branching_factor
        self.height = height
        self.desired_leaves = desired_leaves
        
        self._id = MPI.COMM_WORLD.Get_rank()
        self.parent_id = None
        self.child_ids = []
        self.leaf_sizes = []
    
    
       
    # Prepares the ProcessTree for use.  Should be called by ALL MPI Processes
    # The parent process will organize the remaining processes into a hierarchy by telling them
    # who their parent and children are
    def prepare(self):
        rank = MPI.COMM_WORLD.Get_rank()
        if(rank==0):
            # If we are the main process, build the tree to plan the computation
            self.root, status = grow_tree(self.branching_factor, self.height, self.desired_leaves)
            # Tell all of the other processes who their parent and children are
            self._send_parents_and_children(self.root)

        # Wait for the main process to tell us who our family is
        # Note that the main process tells itself
        self.parent_id, self.child_ids, self.leaf_sizes = MPI.COMM_WORLD.recv(source=0)
        print ( str(self._id) + ") Parent: " + str(self.parent_id) + "  Children: " + str(self.child_ids) + "  Leaf_sizes: " + str(self.leaf_sizes))
    
    # Internal recursive method which should only be called by the MASTER MPI Process
    # It tells each process who its parent and children are
    # Params:
        # ptnode - a node of the virtual process tree
    def _send_parents_and_children(self, ptnode):
            # Each PTNode's _id field corresponds to a MPI process id
            # Tell that process who its parents and children are, and how many
            # leaves are below each of its children
            if(ptnode.parent==None):
                parent_id = None
            else:
                parent_id = ptnode.parent._id
            child_ids = ptnode.get_child_ids()
            leaf_sizes = ptnode.get_child_leaf_sizes()
            
            MPI.COMM_WORLD.send((parent_id, child_ids, leaf_sizes), dest=ptnode._id)
            
            #Make the recursive call so the rest of the tree is also informed
            for child in ptnode.children:
                self._send_parents_and_children(child)
        



# Grows a tree of a given shape and size, if possible
# Params:
    # bf - the desired branching factor of the tree
    # height - the desired height of the tree
    # desired_leaves - should be less than bf^height.  The tree will stop growing
        # once this many leaves have been produced
# Returns:
    # root - a PTNode that represents the root of the tree
    # status - a GrowStatus that contains some stats about the tree's size
def grow_tree(bf, height, desired_leaves):
    status = GrowStatus(bf, height, desired_leaves)
    root = PTNode()
    root.grow(status)
    
    return root, status

# Tracks stats about the status of a tree's growing progress
class GrowStatus:
    num_nodes = 0
    num_leaves = 0
    def __init__(self, bf, height, desired_leaves):
        self.bf = bf
        self.height = height
        self.desired_leaves = desired_leaves
        
        

# Represents a Node in a tree, which is used to organize MPI processes into a hierarchy.
# Note that there are no MPI calls in this class.  The master process should just build
# a tree of PTNodes in order to plan the execution strategy.
class PTNode:
    is_leaf = False
    _id = -1
    parent = None
    leaf_size = 0    
    
    def __init__(self):
        pass
    
    # Recursively grows children nodes until the tree is big enough
    # Will stop growing once the tree is tall enough or has enough leaves
    # Params:
        # status - A GrowStatus that will be modified as the tree grows
        # depth - How deep into the tree is this node?  Root is 0, children are 1, and so on
    # Returns - True if this Node is useful (i.e. it expanded successfully), or
        # False if we already have enough leaves and the tree is done growing.
    def grow(self, status, depth=0):
        
        
        #Tree is already big enough - stop growing it
        if(status.num_leaves >= status.desired_leaves):
            # Return false since this Node is not useful
            return False
        
        # Continue growing
        # Hand out an ID number to this node, and count it towards the total number of nodes
        self._id = status.num_nodes
        status.num_nodes += 1        
        
        
        # This node is a leaf - mark it as such and end the recursion
        self.children = []
        if(depth==status.height):
            self.is_leaf = True
            status.num_leaves += 1
            self.leaf_size = 1
            # Return True since this Node is useful
            return True
        
        
        # Recursively grow children (# of children = bf)
        # We will also sum up the leaf sizes of the children to make this node's leaf size
        self.leaf_size = 0
        for i in range(status.bf):
            potential_child = PTNode()
            # Make the recursive call
            success = potential_child.grow(status, depth+1)
            #Only add that node to the list of children if it is useful, otherwise discard
            if(success):
                potential_child.parent = self
                self.children.append(potential_child)
                self.leaf_size += potential_child.leaf_size

        # Return true since this node (and at least one of its children) is useful
        # This assumption is valid becaue we would have returned False earlier if
        # there were enough leaves.  Therefore, if we got to here, we had to make
        # more recursive calls and grow more leaves.
        return True
    
    def get_child_ids(self):
        return [child._id for child in self.children]
    
    def get_child_leaf_sizes(self):
        return [child.leaf_size for child in self.children]


#  A simple test
if(__name__=="__main__"):
    t = ProcessTree(3,3,15)
    t.prepare()
    
