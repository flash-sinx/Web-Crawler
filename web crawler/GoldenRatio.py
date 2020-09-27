# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 17:27:51 2020

@author: shivanshu bohara
"""
#%%
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime  # For datetime objects
# Import the backtrader platform
import backtrader as bt
import math
import matplotlib.pyplot as plt
from numpy import mean
from statistics import stdev

class GoldenRatio(bt.Strategy):
    lotsize = 10
    
    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.datas[0].datetime.date(0)
        #print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        self.minopen = self.datas[0].open
        self.dayopen = self.datas[1].open
        self.minhigh = self.datas[0].high
        self.dayhigh = self.datas[1].high
        self.minlow = self.datas[0].low
        self.daylow = self.datas[1].low
        self.minclose = self.datas[0].close
        self.dayclose = self.datas[1].close
        self.LongLevel = 0
        self.ShortLevel = 0
        self.stop_price=0
        self.SLorder = None
        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return
        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, %.2f' % order.executed.price)
                if self.position:
                    self.stop_price = order.executed.price*(1-.005)
                    self.log('STOP LOSS CREATE, %.2f' % self.stop_price)
                    self.SLorder = self.close(size = self.lotsize, exectype=bt.Order.Stop, price=self.stop_price)
            elif order.issell():
                self.log('SELL EXECUTED, %.2f' % order.executed.price)
                if self.position:
                    self.stop_price = order.executed.price*(1+.005)
                    self.log('STOP LOSS CREATE, %.2f' % self.stop_price)
                    self.SLorder = self.close(size = self.lotsize, exectype=bt.Order.Stop, price=self.stop_price)
            elif order.isclose():
                self.log('CLOSE EXECUTED, %.2f' % order.executed.price)
            self.bar_executed = len(self)
        #Check cancellation
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
        # Write down: no pending order
        self.order = None
    
    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        #Add trade finances
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))
    
    def next(self):
        currtime = self.datas[0].datetime.time(0)
        sessionstart = datetime.time(9,15,00)
        mytime = datetime.time(9,20,00)
        lastorder = datetime.time(15,0,00)
        squareofftime = datetime.time(15,5,00)
        
        if(currtime==mytime):
            YesterdayHigh = self.dayhigh[0]
            YesterdayLow = self.daylow[0]
            First10minHigh = max(self.minhigh[0],self.minhigh[-1])
            First10minLow = min(self.minlow[0],self.minlow[-1])
            YesterdayRange = YesterdayHigh - YesterdayLow
            Rangeoffirst10min = First10minHigh - First10minLow
            RangeFactor = YesterdayRange + Rangeoffirst10min
            FibRatio = 0.618
            GoldenValue = FibRatio * RangeFactor
            self.LongLevel = self.dayclose[0] + GoldenValue
            self.ShortLevel = self.dayclose[0] - GoldenValue
            
        if(currtime>sessionstart and currtime<lastorder):
            if not self.position:
                if self.minclose[0]>=self.LongLevel:
                    self.log('BUY CREATE, %.2f' % self.minclose[0])
                    self.lotsize = math.floor(cerebro.broker.cash/self.minclose[0])
                    self.order = self.buy(size = self.lotsize)
                                    
                elif self.minclose[0]<=self.ShortLevel:
                    self.log('SELL CREATE, %.2f' % self.minclose[0])
                    self.lotsize = math.floor(cerebro.broker.cash/self.minclose[0])
                    self.order = self.sell(size = self.lotsize)
            
        elif(currtime==squareofftime):
            if self.position:
                self.broker.cancel(self.SLorder)
                self.log('CLOSE CREATE, %.2f' % self.minclose[0])
                self.order = self.close(size = self.lotsize)  
        
if __name__ == '__main__':
    # Create a cerebro entity
    cerebro = bt.Cerebro()
    # Add a strategy
    cerebro.addstrategy(GoldenRatio)
    StartDate = datetime.datetime(2015, 1, 9, 9, 15, 00)
    EndDate = datetime.datetime(2019, 12, 24, 15, 25, 00)
    # Create a Data Feed
    data = bt.feeds.GenericCSVData(
        dataname='banknifty5min.csv',
        fromdate=StartDate,
        todate=EndDate,
        timeframe = bt.TimeFrame.Minutes,
        compression = 5,
        dtformat = ('%Y-%m-%d %H:%M:%S'),
        datetime = 0,
        open = 1,
        high = 2,
        low = 3,
        close = 4,
        volume = 5,
        openinterest = -1)
    
    cerebro.adddata(data)
    cerebro.resampledata(data, timeframe=bt.TimeFrame.Days, compression=1)
    # Add the Data Feed to Cerebro
    
    # Set our desired cash start
    #cerebro.broker.set_slippage_perc(perc = 0.01, slip_open=True)
    InitialValue = 2500000
    Leverage = 1
    Commission = 0.00008
    cerebro.broker.set_coc(True)
    cerebro.broker.setcash(InitialValue)
    cerebro.broker.setcommission(commission=Commission,mult=Leverage)
    '''
    Since the margin for niftybank futures varies is around 8%, but it depends on volatality and other factors
    I checked with zerodha, for current conditions(highly volatile) margin requirements are very high, i.e, around 1Lakh for 1 lot costing about 3.66L
    Plus having the intrady trade with stop loss provides extra leverage
    So, I assume the leverage to be around 15
    '''
    # Print out the starting conditions
    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name = 'returnsmonthly', timeframe=bt.TimeFrame.Months)
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name = 'returnsyearly', timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer)
    cerebro.addanalyzer(bt.analyzers.Transactions)
    cerebro.addanalyzer(bt.analyzers.DrawDown)
    cerebro.addanalyzer(bt.analyzers.Returns, timeframe=bt.TimeFrame.Years)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio)
    cerebro.addanalyzer(bt.analyzers.SQN)
    cerebro.addanalyzer(bt.analyzers.TimeDrawDown, timeframe=bt.TimeFrame.Months)
   
    # Run over everything
    results = cerebro.run()
    strat0 = results[0]
    FinalValue = cerebro.broker.getvalue()
    print('Final Portfolio Value: %.2f' % FinalValue)
    cerebro.plot(style ='candlebars')
    
    timereturnsmonthly = strat0.analyzers.returnsmonthly.get_analysis()
    timereturnsyearly = strat0.analyzers.returnsyearly.get_analysis()
    tradeanalysis = strat0.analyzers.tradeanalyzer.get_analysis()
    transactions = strat0.analyzers.transactions.get_analysis()
    drawdown = strat0.analyzers.drawdown.get_analysis()
    returns = strat0.analyzers.returns.get_analysis()
    sharperatio = strat0.analyzers.sharperatio.get_analysis()
    sqn = strat0.analyzers.sqn.get_analysis()
    monthlydrawdown = strat0.analyzers.timedrawdown.get_analysis()
    
    '''
    import csv
    with open("godenratio.csv", "w", newline='') as outfile:
        csvwriter = csv.writer(outfile)
        for key,value in monthlydrawdown.items():
            csvwriter.writerow((key,value))
    '''
    
    TotalTrades = tradeanalysis['total']['total']
    TotalWon = tradeanalysis['won']['total']
    TotalLost = tradeanalysis['lost']['total']
    WinPercent = 100*TotalWon/(TotalWon+TotalLost)
    GrossProfit = tradeanalysis['won']['pnl']['total']
    GrossLoss = tradeanalysis['lost']['pnl']['total']
    ProfitFactor = GrossProfit/abs(GrossLoss)
    MaxProfit = tradeanalysis['won']['pnl']['max']
    MaxLoss = tradeanalysis['lost']['pnl']['max']
    AvgWin = tradeanalysis['won']['pnl']['average']
    AvgLoss = tradeanalysis['lost']['pnl']['average']
    AvgProfit = tradeanalysis['pnl']['net']['average']
    NetProfit = tradeanalysis['pnl']['net']['total']
    AvgLen = tradeanalysis['len']['average']
    WinLen = tradeanalysis['len']['won']['average']
    LossLen = tradeanalysis['len']['lost']['average']
    MaxDD = drawdown['max']['drawdown']
    MaxMonthlyDD = monthlydrawdown['maxdrawdown']
    MaxDDlen = math.ceil(drawdown['max']['len']/75)
    SharpeRatio = sharperatio['sharperatio']
    SQN = sqn['sqn']
    TotalGrowthReturns = (FinalValue-InitialValue)*100/InitialValue
    CAGR = returns['rnorm100']
    DrawDown = 0
    dates_toplot = [StartDate]
    portfolio_value_toplot = [InitialValue]
    
    import xlsxwriter
    workbook = xlsxwriter.Workbook('GoldenRatioSL.xlsx')
    bold = workbook.add_format({'bold': True})
    format2 = workbook.add_format({'num_format': 'yyyy'})
    format3 = workbook.add_format({'num_format': 'mmm-yy'})
    format4 = workbook.add_format({'num_format': 'dd-mm-yy'})
    format5 = workbook.add_format({'num_format': 'hh:mm:ss'})
    returns = workbook.add_worksheet('Returns')
    returns.write(0,0,'Year', bold)
    returns.write(0,1,'% Returns', bold)
    i=1
    for key,value in timereturnsyearly.items():
        returns.write(i,0,key,format2)
        returns.write(i,1,value*100)
        i += 1
    i+=2
    returns.write(i,0,'Month', bold)
    returns.write(i,1,'% Returns', bold)
    i+=1
    for key,value in timereturnsmonthly.items():
        returns.write(i,0,key,format3)
        returns.write(i,1,value*100)
        i += 1
    
    j = 3
    k = 2
    analysis = workbook.add_worksheet('Analysis')
    analysis.set_column('C:C', 30)
    analysis.write(j-1,k,'Stats', bold)
    analysis.write(j-1,k+1,'Data', bold)
    analysis.write(j,k,'Total Trades')
    analysis.write(j,k+1,TotalTrades)
    analysis.write(j+1,k,'Total Won')
    analysis.write(j+1,k+1,TotalWon)
    analysis.write(j+2,k,'Total Lost')
    analysis.write(j+2,k+1,TotalLost)
    analysis.write(j+3,k,'Win percentage')
    analysis.write(j+3,k+1,WinPercent)
    analysis.write(j+4,k,'Net Profit')
    analysis.write(j+4,k+1,NetProfit)
    analysis.write(j+5,k,'Total Profit%')
    analysis.write(j+5,k+1,TotalGrowthReturns)
    analysis.write(j+6,k,'CAGR')
    analysis.write(j+6,k+1,CAGR)
    analysis.write(j+7,k,'Gross Profit')
    analysis.write(j+7,k+1,GrossProfit)
    analysis.write(j+8,k,'Gross Loss')
    analysis.write(j+8,k+1,GrossLoss)
    analysis.write(j+9,k,'Profit Factor')
    analysis.write(j+9,k+1,ProfitFactor)
    analysis.write(j+10,k,'Max Profit in 1 trade')
    analysis.write(j+10,k+1,MaxProfit)
    analysis.write(j+11,k,'Max Loss in 1 trade')
    analysis.write(j+11,k+1,MaxLoss)
    analysis.write(j+12,k,'Average Profit in winning trade')
    analysis.write(j+12,k+1,AvgWin)
    analysis.write(j+13,k,'Average Loss in losing trade')
    analysis.write(j+13,k+1,AvgLoss)
    analysis.write(j+14,k,'Average Profit in a trade')
    analysis.write(j+14,k+1,AvgProfit)
    analysis.write(j+15,k,'Average Length')
    analysis.write(j+15,k+1,AvgLen)
    analysis.write(j+16,k,'Average Winning Length')
    analysis.write(j+16,k+1,WinLen)
    analysis.write(j+17,k,'Average Losing Length')
    analysis.write(j+17,k+1,LossLen)
    analysis.write(j+18,k,'Max DrawDown')
    analysis.write(j+18,k+1,MaxDD)
    analysis.write(j+19,k,'Max DrawDown Length in days')
    analysis.write(j+19,k+1,MaxDDlen)
    analysis.write(j+20,k,'Max Monthly DrawDown')
    analysis.write(j+20,k+1,MaxMonthlyDD)
    analysis.write(j+21,k,'Sharpe Ratio')
    analysis.write(j+21,k+1,SharpeRatio)
    analysis.write(j+22,k,'SQN')
    analysis.write(j+22,k+1,SQN)
    
    graph = workbook.add_worksheet('Graph')
    graph.insert_image('A0', 'grplot.png')
    
    tradelog = workbook.add_worksheet('Trade Log')
    tradelog.write(0,0,'Entry Date', bold)
    tradelog.write(0,1,'Entry Time', bold)
    tradelog.write(0,2,'Position', bold)
    tradelog.write(0,3,'Price', bold)
    tradelog.write(0,4,'Quantity', bold)
    tradelog.write(0,5,'Cost', bold)
    tradelog.write(0,6,'Exit Date', bold)
    tradelog.write(0,7,'Exit Time', bold)
    tradelog.write(0,8,'Price', bold)
    tradelog.write(0,9,'Quantity', bold)
    tradelog.write(0,10,'Return', bold)
    tradelog.write(0,11,'Profit', bold)
    tradelog.write(0,12,'%Profit', bold)
    tradelog.write(0,13,'DrawDown', bold)
    i=0
    buy = 0
    for key,value in transactions.items():
        if(i%2==0):
            tradelog.write((int)(i/2+1),0,key,format4)
            tradelog.write((int)(i/2+1),1,key,format5)
            if(value[0][0]>0):
                tradelog.write((int)(i/2+1),2,'Long')
            else:
                tradelog.write((int)(i/2+1),2,'Short')
            tradelog.write((int)(i/2+1),3,value[0][1])
            tradelog.write((int)(i/2+1),4,value[0][0])
            buy = value[0][4]
            tradelog.write(i/2+1,5,value[0][4])
        else:
            tradelog.write((int)((i+1)/2),6,key,format4)
            dates_toplot.append(key)
            tradelog.write((int)((i+1)/2),7,key,format5)
            tradelog.write((int)((i+1)/2),8,value[0][1])
            tradelog.write((int)((i+1)/2),9,value[0][0])
            tradelog.write((int)((i+1)/2),10,value[0][4])
            profitintrade = value[0][4]+buy
            portfolio_value_toplot.append(portfolio_value_toplot[-1]+profitintrade)
            tradelog.write((int)((i+1)/2),11,profitintrade)
            percentprofit = profitintrade*100/abs(buy)
            tradelog.write((int)((i+1)/2),12,percentprofit)
            DrawDown = min(0,DrawDown+profitintrade)
            tradelog.write((int)((i+1)/2),13,DrawDown)
        i+=1
    
    
    years_toplot = []
    years_value_toplot = []
    for d in timereturnsyearly.keys():
        years_toplot.append(d.year)
    for v in timereturnsyearly.values():
        years_value_toplot.append(v*100)
    plt.bar(years_toplot, years_value_toplot, color='red')
    plt.title('Yearly Returns(in %)')
    plt.savefig('yearlyreturns.png')
    returns.insert_image('F3', 'yearlyreturns.png')
    returns.write(0,2,'Average', bold)
    returns.write(1,2,mean(years_value_toplot))
    returns.write(0,3,'StDev', bold)
    returns.write(1,3,stdev(years_value_toplot))
    plt.show()
    
    fig_size = plt.rcParams["figure.figsize"]
    fig_size[0] = 10
    fig_size[1] = 7.5
    plt.rcParams["figure.figsize"] = fig_size
    months_toplot = []
    months_value_toplot = []
    for d in timereturnsmonthly.keys():
        months_toplot.append(str(d.month)+"/"+str(d.year))
    for v in timereturnsmonthly.values():
        months_value_toplot.append(v*100)
    plt.xticks(rotation = 'vertical')
    plt.bar(months_toplot, months_value_toplot, color='green')
    plt.subplots_adjust(bottom = 0.16, left = 0.05, right = 0.98)
    plt.title('Monthly Returns(in %)')
    plt.savefig('monthlyreturns.png')
    returns.insert_image('F27', 'monthlyreturns.png')
    returns.write(len(years_value_toplot)+2,2,'Average', bold)
    returns.write(len(years_value_toplot)+3,2,mean(months_value_toplot))
    returns.write(len(years_value_toplot)+2,3,'StDev', bold)
    returns.write(len(years_value_toplot)+3,3,stdev(months_value_toplot))
    plt.show()
    
    plt.plot(dates_toplot,portfolio_value_toplot)
    plt.title('Portfolio Value')
    plt.savefig('Portfolio.png')
    returns.insert_image('F63', 'Portfolio.png')
    plt.show()
    
    workbook.close()    