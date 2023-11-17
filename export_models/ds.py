from base import *
from helper import *

class Tree(FileChunk):
    def analyze(self):
        self.word()
        self.rootPtr = self.word()
        self.nodes = {}
        self.roots = [self.node(self.rootPtr)]
        while self.roots[-1].next:
            self.roots.append(self.node(self.roots[-1].next))
        self.crawl()

    def node(self, addr):
        newNode = TreeNode(self.f, self.absolute + addr - 0x4, 0x10, "Node").analyze()
        newNode.addr = addr
        self.nodes[addr] = newNode
        return newNode
    
    def description(self):
        desc = super().description()
        stack = [[root, 0] for root in self.roots]
        # print ('\n'.join([hex(x) + " => " + self.nodes[x].childStr(self.nodes) for x in list(self.nodes.keys())]))
        while len(stack):
            node, level = stack.pop()
            desc += '\n' + '  ' * level + hex(node.id)
            child = node.firstChild
            # print("\nchild is " + hex(child))
            while child != 0:
                childNode = self.nodes[child]
                stack.append([childNode, level + 1])
                child = childNode.next
        # exit(0)
        return desc

    def crawl(self):
        stack = [root for root in self.roots]
        while len(stack):
            node = stack.pop()
            child = node.firstChild
            while child:
                childNode = self.node(child)
                stack.append(childNode)
                child = childNode.next

    # Return a list of 'hierarchy node' objects with
        # addr: the address immediately following a node in the tree
        # children: a list of 'hierarchy node' objects that are children of that node
    def hierarchy(self):
        # Returned, the list of base hierarchy nodes in the tree
        hierarchy = []
        # A list of objects that have not had their children array populated
        stack = []
        for node in self.roots:
            node_obj = Object()
            # 0xc offset is immediately after the node
            # Nodes are 0x10 bytes long, but the addresses used in the tree are relative to the start of the tree - 0x4
            node_obj.addr = node.addr + 0xc
            node_obj.children = []
            node_obj.parent = None
            hierarchy.append(node_obj)
            stack.append(node_obj)
        while len(stack):
            parent = stack.pop()
            child_addr = self.nodes[parent.addr - 0xc].firstChild
            while child_addr in self.nodes:
                child = self.nodes[child_addr]
                child_obj = Object()
                child_obj.addr = child.addr + 0xc
                child_obj.children = []
                child_obj.parent = parent
                parent.children.append(child_obj)
                stack.append(child_obj)
                child_addr = child.next
        return hierarchy

class TreeNode(FileChunk):
    def analyze(self):
        self.prev = self.word()
        self.next = self.word()
        self.parent = self.word()
        self.firstChild = self.word()
        return self
    def description(self):
        return ''
    def childStr(self, nodes):
        out = []
        child = self.firstChild
        while child in nodes:
            out.append('{:04x}'.format(child))
            child = nodes[child].next
        return ', '.join(out)