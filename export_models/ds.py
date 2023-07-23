from base import *

class Tree(FileChunk):
    def analyze(self, offset = None):
        self.offset = self.word()
        if offset != None:
            self.offset = offset
        self.rootPtr = self.word()
        self.nodes = {}
        self.indexes = {}
        self.roots = [self.node(self.rootPtr)]
        while self.roots[-1].next:
            self.roots.append(self.node(self.roots[-1].next))
        self.crawl()

    def node(self, addr):
        newNode = TreeNode(self.f, self.absolute + addr + self.offset, 0x10, "Node").analyze()
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
    
    def nodeByIndex(self, index):
        return self.indexes[index]
    
    def nodeByOffset(self, offset):
        return self.nodes[offset]

    def crawl(self):
        stack = [root for root in self.roots]
        while len(stack):
            node = stack.pop()
            child = node.firstChild
            while child:
                childNode = self.node(child)
                stack.append(childNode)
                child = childNode.next
        sortedNodes = list(self.nodes.keys())
        sortedNodes.sort()
        for ind, key in enumerate(sortedNodes):
            self.nodes[key].id = ind
            self.indexes[ind] = self.nodes[key]

class TreeNode(FileChunk):
    def analyze(self):
        self.prev = self.word()
        self.next = self.word()
        self.parent = self.word()
        self.firstChild = self.word()
        self.id = None
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