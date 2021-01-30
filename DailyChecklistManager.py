from notion.client import NotionClient
from notion.block import *
from notion.collection import *
import sys
import datetime
import notion
import asyncio
import argparse
import time
#import configparser

class DailyChecklistManager:
    _client=None
    _checklistPageUrl=''
    _routinePageUrl=''
    def __init__(self):
        pass
    def cycle():
        return ['일간','주간','월간']
    def status():
        return ['진행 중', '미흡', '완벽']
    def weekday():
        return ['월', '화', '수', '목', '금', '토', '일']
    def client():
        return DailyChecklistManager._client
    def checklistPageUrl():
        return DailyChecklistManager._checklistPageUrl
    def routinePageUrl():
        return DailyChecklistManager._routinePageUrl
    def notionBaseUrl():
        return 'https://www.notion.so/'

def getDateFormat(date):
    return date.strftime(f'%y/%m/%d({DailyChecklistManager.weekday()[date.weekday()]})')

async def addDailyChecklist(client):
    checklistPage = client.get_block(DailyChecklistManager.checklistPageUrl())
    if checklistPage is None:
        print('Failed to get checklist page')
        return False

    checklistTable = checklistPage.collection
    if checklistTable is None:
        print('Failed to get checklist table')
        return False

    newChecklist = await addNewChecklistToTable(checklistTable)
    if newChecklist is None:
        print('Failed to create new checklist')

    dateToday = datetime.date.today()

    newChecklist.title = getDateFormat(dateToday)
    newChecklist.date = dateToday
    newChecklist.status = DailyChecklistManager.status()[0]

    routineTickets = getRoutineTickets(client)
    if routineTickets is None or len(routineTickets) <= 0:
        print('Failed to get routine tickets')
        return False

    for ticket in routineTickets:
        # 해당 날짜에 필요한 작업인지를 체크
        if ticket.cycle == DailyChecklistManager.cycle()[0]\
        and DailyChecklistManager.weekday()[datetime.date.today().weekday()] in ticket.weekday:
            newTicket = await addNewTodoToChecklist(newChecklist, ticket.title)
            for todo in ticket.children:
#                newTodo = newTicket.children.add_new(TodoBlock, title=todo.title)
                await copyChildren(todo, newTicket)
    return True

async def addNewChecklistToTable(checklistTable):
    newRow = None
    try:
        newRow = checklistTable.add_row()
    except HttpError as e:
        time.sleep(5)
        dateToday = datetime.datetime.today()
        newRow = checklistTable.get_rows(search=getDateFormat(dateToday))[0]
    return newRow

async def addNewTodoToChecklist(checklist, title):
    return checklist.children.add_new(TodoBlock, title=title)  

def getRoutineTickets(client):
    routinePage = client.get_block(DailyChecklistManager.routinePageUrl())
    if routinePage is None:
        print('Failed to get routine works page')
        return None

    routineCollection = routinePage.collection
    if routineCollection is None:
        print('Failed to get routine collection')
        return None

    tickets = routineCollection.get_rows()
    if len(tickets) <= 0:
        print('No valid routine tickets')
        return None
    return tickets

async def copyChildren(src, dest):
    newDest = dest.children.add_new(type(src), title=src.title)
    for child in src.children:
        await copyChildren(child, newDest)
    return

async def updateLastDailyChecklist(client):
    checklistPage = client.get_block(DailyChecklistManager.checklistPageUrl())
    if checklistPage is None:
        print('Failed to get checklist page')
        return False

    checklistTable = checklistPage.collection
    if checklistTable is None:
        print('Failed to get checklist table')
        return False

    datetimeToday = datetime.datetime.today()
    checklist = checklistTable.get_rows(search=getDateFormat(datetimeToday))[0]

    hasMissingItems, missings = getUncheckedItems(client, checklist)

    if hasMissingItems:
        if datetimeToday.hour >= 23:
            checklist.status = DailyChecklistManager.status()[1]
            missedString = ''
            checklist.missed = '\n'.join(missings)
        else:
            checklist.status = DailyChecklistManager.status()[0]
            checklist.missed = ''
    else:
        checklist.status = DailyChecklistManager.status()[2]
    return True

def getUncheckedItems(client, checklist):
    result = False
    unchecked = []
    print('Searching for unchecked items...')
    for ticket in checklist.children:
        if isinstance(ticket, TodoBlock):
            if not ticket.checked:
                remainSubTodo = False
                for subTodo in ticket.children:
                    if not subTodo.checked:
                        remainSubTodo = True
                        break
                if remainSubTodo:
                    result = True
                    unchecked.append(ticket.title)
                else:
                    ticket.checked = True
            else:
                continue
        else:
            if ticket.title != '':
                print(f'{ticket.title}:{ticket._type}')
    print('Unchecked item search finished')
    return result, unchecked

##########
# 블럭을 복사하는 함수 - 직접 구현하는 것 보다 api에서 정식 지원해주는 것을 기다리는게 나아보임
#
#async def copyBlock(src, dest):
#    if isinstance(BasicBlock) is True:
#        if src._type == 'text':
#            return dest
#        elif src._type == 'header':
#        elif src._type == 'sub_header':
#        elif src._type == 'sub_sub_header':
#        elif src._type == 'page':
#        elif src._type == 'to_do':
#        elif src._type == 'bulleted_list':
#        elif src._type == 'numbered_list':
#        elif src._type == 'toggle':
#        elif src._type == 'code':
#        elif src._type == 'quote':
#        elif src._type == 'callout':
#        elif src._type == 'equation':
#        else:
#            print(f'Invalid type of block:{src._type}')
#            return None
#    elif isinstance(Embed

async def main(argc, argv):

    funcs = { \
        'update':updateLastDailyChecklist\
        ,'U':updateLastDailyChecklist\
        ,'add':addDailyChecklist\
        ,'A':addDailyChecklist
    }

    parser = argparse.ArgumentParser(description='노션 일일 체크리스트 관리 스크립트')
    parser.add_argument('--mode', '-m', choices=funcs.keys(), help='동작 방식.')
    parser.add_argument('--token', '-t', required=True, help='notion token_v2')
    parser.add_argument('--url-checklist', '-uc', help='체크리스트 테이블이 존재하는 페이지의 url')
    parser.add_argument('--url-routine', '-ur', help='반복성 루틴이 존재하는 칸반보드 페이지의 url')
    #parser.add_argument('--config', '-c', help='설정 값 파일의 경로')

    args = parser.parse_args()
    
    if args == None:
        result = False
        print("Failed to parse arguments.")
        return result

    if not args.url_checklist.startswith(DailyChecklistManager.notionBaseUrl()):
        DailyChecklistManager._checklistPageUrl += DailyChecklistManager.notionBaseUrl()
    DailyChecklistManager._checklistPageUrl += args.url_checklist

    if not args.url_routine.startswith(DailyChecklistManager.notionBaseUrl()):
        DailyChecklistManager._routinePageUrl += DailyChecklistManager.notionBaseUrl()
    DailyChecklistManager._routinePageUrl += args.url_routine

    client = NotionClient(token_v2=args.token)
    
    if client == None:
        result = False
        print("Failed to access on notion. Please check your notion api token")
        return result
    
    DailyChecklistManager._client = client

    result = await funcs[args.mode](client)
    
    #todo - 칸반보드 주소와 체크리스트 주소를 ini 파일에서 읽어올 수 있도록 할 것

    return result

if __name__ == '__main__':
    asyncio.run(main(len(sys.argv), sys.argv))