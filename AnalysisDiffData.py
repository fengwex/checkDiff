#!/usr/bin/python
# -*- coding: UTF-8 -*-

import re
from git import Repo
from itertools import islice


class AnalysisDiffData(object):
    def __init__(self, path=None, originBranch="HEAD^", currentBranch="HEAD"):
        try:
            if path:
                self.originBranch = originBranch
                self.currentBranch = currentBranch
                newContent = self.readContent()
                self.content = newContent.split('\n')
        except Exception as e:
            print("初始化错误信息：%s", e)
        else:
            # 初始化参数
            self.classes = {}  # 类集
            self.methods = {}  # 方法集
            self.delClasses = {}  # 需删除类名
            self.classList = []  # 类起始行列表
            self.methodList = []  # 方法起始行列表
            self.classLines = []  # 类区间行列表
            self.methodLines = []  # 方法区间行列表

    def readContent(self):
        """  过滤 git diff 文件中的注释行  """
        # 读取 git diff 的内容
        repo = Repo(path)
        contents = repo.git.diff(self.originBranch, self.currentBranch)
        # print(content)
        # 过滤文件中的注释行
        with open("./diffdemo.txt", "w", encoding="UTF-8") as file:
            for content in contents.split('\n'):
                line = content.replace(" ", "")
                # 过滤以下注释格式的行
                if not line.startswith("-*") and not line.startswith("-/*") and not line.startswith(
                        "*") and not line.startswith("/*"):
                    file.write(content + "\n")
        with open("./diffdemo.txt", "r", encoding="utf-8") as f:
            newContent = f.read()
        return newContent

    def getClassMethodLine(self):
        """  获取每个 类、方法 的起始行 """
        for index in range(len(self.content)):
            line = self.content[index]
            # 获取类名
            if line.startswith('diff --git'):
                className = line.replace('/', '.').split('.')[-2]
                self.classes[index] = className
                self.classList.append(index)
            #  获取需删除的类名
            if line.startswith('diff --git') and line.endswith(".xml"):
                delName = line.replace('/', '.').split('.')[-2]
                self.delClasses[index] = delName
            # 通过行内容获取方法名
            if not line.endswith(";") and line.count("=") == 0:
                elementList = line.split()
                for element in elementList:
                    # 正则匹配包含方法行
                    matchElement = re.match("^\w+\(", element)
                    if matchElement is not None and "." not in element:
                        # 获取匹配到元素的下标
                        elementIndex = elementList.index(element)
                        if elementIndex > 0:
                            # 匹配到的方法元素前一个元素存在且符合某规则，认为为方法名
                            match = re.match("^\w+", elementList[elementIndex - 1])
                            # if match is not None and match.group() not in ["AND", "LIKE", "SELECT"]:
                            if match is not None:
                                # 获取方法名
                                methodName = matchElement.group().split("(")[0]
                                self.methods[index] = methodName
                                self.methodList.append(index)
                                break
        # 类起始行列表
        self.classList.append(len(self.content))
        # 方法起始行列表
        self.methodList.append(len(self.content))
        print("类集:classes------", self.classes)
        print("方法集:methods------", self.methods)
        print("需删除类名:delClasses------", self.delClasses)
        print("类起始行列表:classList-----", self.classList)
        print("方法起始行列表:methodList-----", self.methodList)
        return self.classes, self.methods, self.classList, self.methodList, self.delClasses

    def getClassesIntervalLine(self):
        """  获取所有类 起始、结束行 列表 """
        # classes, methods, classList, methodList, delClasses = self.getClassMethodLine()
        count = 0
        # 获取所有类的起始、结束行范围
        for key, value in self.classes.items():
            # 每个类起始、结束行列表
            myList = []
            # newClasses = {}
            myList.append(key)
            # 当前类的结束行就是 下一个类的起始行
            endLine = self.classList[count + 1]
            myList.append(endLine)
            # newClasses[value] = myList
            self.classLines.append(myList)
            count += 1
        print("类区间行列表：classLines-----", self.classLines)
        return self.classLines

    def getMethodIntervalLine(self):
        """  获取所有方法 起始、结束行 列表 """
        # classes, methods, classList, methodList, delClasses = self.getClassMethodLine()
        # classLines = self.getClassesIntervalLine()
        count = 0
        # 获取所有方法的起始、结束行范围
        for classLine in self.classLines:
            for key, value in self.methods.items():
                # 当方法的起始行大于当前类的结束行，取下一个类的结束行
                if key > classLine[1]:
                    break
                # 判断方法的结束行是否在当前类的结束行内
                if classLine[0] <= key <= classLine[1]:
                    # 每个方法起始、结束行列表
                    myList = []
                    myList.append(key)
                    # 当前方法的结束行就是 下一个方法起始行
                    endLine = self.methodList[count + 1] - 1
                    # 如果方法的结束行大于当前类的结束行，则取当前类结束行为当前方法的结束行
                    if endLine > classLine[1]:
                        endLine = classLine[1]
                    myList.append(endLine)
                    self.methodLines.append(myList)
                    count += 1
        print("方法区间行列表：methodLines-----", self.methodLines)
        return self.methodLines

    def getChangeMethod(self):
        """  获取有变更的方法行列表 """
        try:
            methodLines = self.getMethodIntervalLine()
            changeList = []
            for method in methodLines:
                for line in islice(self.content, method[0], method[1]):
                    # 如果在方法区间行内 以"+"、"-"作为行开头，认为方法有改变
                    if line.startswith("+") or line.startswith("-"):
                        changeList.append(method[0])
                        break
            print("方法改变行列表：changeList-----", changeList)
            return changeList
        except Exception as e:
            print("getChangeMethod方法错误信息：%s", e)

    def mergeClassMethod(self):
        """  整合类对应的方法 """
        classes, methods, classList, methodList, delClasses = self.getClassMethodLine()
        classLines = self.getClassesIntervalLine()
        changeList = self.getChangeMethod()
        finalList = []
        # 合并类对应的方法
        # for key, value in classes.items():
        for classLine in classLines:
            # 方法列表
            finalDict = {}
            methodLists = []
            # valueList = []
            for num in changeList:
                # 根据方法行获取方法名
                method = methods[num]
                # 当方法的起始行大于当前类的结束行，取下一个类的结束行
                if num > classLine[1]:
                    break
                # 当方法的结束行在当前类的结束行内，则添加方法到当前类下
                if classLine[0] <= num <= classLine[1]:
                    methodLists.append(method)
            # 当前类中方法不为空，且类名不在需删除类名字典中
            if methodLists and not delClasses.__contains__(classLine[0]):
                finalDict[classes[classLine[0]]] = methodLists
                finalList.append(finalDict)
        # print("类关联方法:finalDict-----", finalDict)
        print("类关联方法:finalList-----", finalList)
        return finalList


if __name__ == '__main__':
    # 本地仓库地址
    path = "E:/learn/java/java_demo"
    getDiff = AnalysisDiffData(path=path)
    getDiff.mergeClassMethod()
