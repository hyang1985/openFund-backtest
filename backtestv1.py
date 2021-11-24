# -*- coding: utf-8 -*-
"""
Created on Sun Nov 21 11:01:33 2021

@author: huyang
please contact me with hyang1985@hotmail.com
"""

#from libs import libs

import pandas as pd
import numpy as np

import datetime

import math

import empyrical as em

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams['font.sans-serif'] = ['SimHei']  # 中文字体设置-黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决保存图像是负号'-'显示为方块的问题

from sklearn.preprocessing import MinMaxScaler

from WindPy import w
w.start()

#功能：返回一个起止日期时间段内所有的日期
#参数：beginDate：开始日期;endDate:结束日期
def dateRange(beginDate, endDate):
    dates = []
    dt = datetime.datetime.strptime(beginDate, "%Y-%m-%d")
    date = beginDate[:]
    while date <= endDate:
        dates.append(date)
        dt = dt + datetime.timedelta(1)
        date = dt.strftime("%Y-%m-%d")
    return dates

#功能：获取某只开放式基金的净值
#参数：fund_code:基金代码；tradedate：交易日    
def Cal_NetValue(fund_code,tradedate):
    v = w.wsd(fund_code, "nav", tradedate,tradedate, "").Data[0][0]
    if v=='CWSDService: No data.':
        return np.nan
    else:
        return v
    
#功能：获取开放式基金列表里所有基金的净值
#参数：fund_code_list:基金代码列表；tradedate：交易日    
def Cal_Fundlist_NetValue(fund_code_list,*date):
    if(type(fund_code_list)!=list):
        return np.nan
    if(len(date)==1):
        v = w.wsd(fund_code_list, "nav", date[0], "").Data[0]
        if len(v)<=1:
        #此种情况万得返回['CWSDService: No data.']
            return np.nan
    if(len(date)==2):
        v = w.wsd(fund_code_list, "nav", date[0],date[1], "")
        return v
    
#功能：获取某个指数的收盘价，作为比较基准
#参数：tradedate为交易日,code一般为指数代码如沪深300，中证500，默认为沪深300    
def get_BenchmarkValue(code="000300.SH",*date):
    if(len(date)==1):
        v = w.wsd(code, "close", date[0], date[0],"").Data[0]
        return v
    if(len(date)==2):
        v = w.wsd(code, "close", date[0], date[1],"")
        return v
#功能：定义账户类
class Account(object):
    def __init__(self,init_base):
    #属性：init_base:初始账户;fund_list:基金持仓
        self.init_base=init_base
        self.fund_list={}
        pass
    #功能：获取持仓基金列表
    def getbase(self):
        return self.account.init_base
    #功能：获取账户
    def get_initbase(self):
        return self.init_base
    
class fund_backTest():
    
    def __init__(self, begin_date, end_date,init_base):
        self.begin_date=begin_date
        self.end_date=end_date
        self.account=Account(init_base)
        self.flag=0
        self.data=pd.DataFrame(index=dateRange(self.begin_date,self.end_date),columns=['init_base','fund_list','flag'])
        self.data['fund_list']=self.data['fund_list'].astype('object')
        #for date in dateRange(self.begin_date,self.end_date):
        #    self.data.update({date:{}})
        #    self.data[date].update({'init_base':init_base,'fund_list':{},'flag':self.flag})
    
    #功能：申购或买入函数，用于买入指定数量的基金
    #参数：fundcode：基金代码;num：申购数量;date：交易日期
    def buy(self,fundcode,num,date):
        #计算交易日净值
        netvalue=Cal_NetValue(fundcode, date)
        #如果申购额度大于账户余额则交易无效
        if netvalue*num>self.account.init_base:
            pass
        else:
            self.account.init_base-=netvalue*num
        ##获取fundlist中fundcode的持仓，如果有则相加，如果没有持仓则更新
        if fundcode not in self.account.fund_list.keys():
            self.account.fund_list.update({fundcode:num})
        else :
            remain_num=self.account.fund_list[fundcode]+num
            self.account.fund_list.update({fundcode:remain_num})
        
        #更新从购买日之后起的data
        self.update_data(date,self.end_date,self.account.init_base,self.account.fund_list.copy())   
        
    def buy_list(self,fundcode_list,date):
        #传入的基金列表类型必须为列表
        if(type(fundcode_list)!=list):
            pass
        #计算购买清单长度
        l=len(fundcode_list)
        #每一只基金总共有n_quota元用于申购
        n_quota=math.floor(self.account.init_base/l)
        for code in fundcode_list:
            netvalue=Cal_NetValue(code, date)
            #计算某种基金申购额度，采用金额/净值并向下取整
            num=math.floor(n_quota/netvalue)
            self.buy(code,num,date)
    
    #赎回或卖出函数，用于卖出指定数量的基金    
    def sell (self,fundcode,num,date):
        netvalue=Cal_NetValue(fundcode, date)
        #如果持仓列表里没有这个基金，则跳过不执行
        if fundcode not in self.account.fund_list.keys():
            pass
        #如果持仓列表里有这个基金，则可以卖出
        else :
            remain_num=self.account.fund_list[fundcode]-num
            #如果小于等于零，则相当于全部卖出
            if(remain_num<=0):
                
                self.account.init_base+=self.account.fund_list[fundcode]*netvalue
                self.account.fund_list.pop(fundcode)
            else: 
                self.account.fund_list.update({fundcode:remain_num})
                self.account.init_base+=num*netvalue   
        #更新从购买日之后起的data
        self.update_data(date,self.end_date,self.account.init_base,self.account.fund_list.copy())  
    
    #清仓或卖出所有函数，用于将持仓的基金全部卖出
    def sell_all (self,date):
        for k,v in self.data.loc[date]['fund_list'].items():
            self.sell(k,v,date)
           
    #更新持仓函数，用于每次有买入或卖出时更新账户并更新data
    def update_data(self,begin_date,end_date,*args):
        self.flag=self.flag+1
        self.data.loc[begin_date:end_date,'flag']=self.flag
        self.data.loc[begin_date:end_date,'init_base']=args[0]
        for date in dateRange(begin_date,end_date):
            self.data.at[date,'fund_list']=args[1]
        #    new_init_base=args[0]
        #    new_fund_list=args[1]
            #self.data.update({date:{'init_base':args[0],'fund_list':args[1]}})  
        pass
    
    #盘后处理函数，结束之后调用,用于计算每日收益，alpha，beta等
    def handle_data(self,log=True):
        #构造收益矩阵，矩阵中行为日期，列包含持仓市值，资金余额，alpha，beta等
        df_returns=self.data[self.data['flag'].isna()==False].copy()
        #df_returns['nav']=0
        #df_returns['nav']=df_returns['nav'].astype('object')
        #将data按照flag划分为若干个时间区间，按照我们对flag的定义，每有一次交易时flag会+1，如果没有交易则不变，那么每个flag区间内持仓是一样的
        #分别计算每个flag内持仓的市值和总资产，用于进行后续收益率，风险的计算
        flags=df_returns['flag'].unique()
        df_returns['nav']=0
        df_returns['nav']=df_returns['nav'].astype('object')
        for flag in flags:
            begin_date=df_returns[df_returns['flag']==flag].index[0]
            end_date=df_returns[df_returns['flag']==flag].index[-1]
            ###第一个指标，持仓市值###
            #计算持仓市值
            fund_list=list(df_returns.loc[begin_date]['fund_list'].keys())
            if(len(fund_list)==0):
                continue
            #持仓基金列表对应的持仓数量
            nums=list(df_returns.loc[begin_date]['fund_list'].values())
            navs=Cal_Fundlist_NetValue(fund_list,begin_date,end_date)
            valid_index=[]
            #将返回的基金净值转换为numpy以便切片
            d=np.array(navs.Data)
            i=0
            for t in navs.Times:
                #将返回的时间转换为字符串型
                idx=t.strftime("%Y-%m-%d")
                
                #情况1:形如下列形式,多余1只基金，多个返回日期
                #.ErrorCode=0
                #.Codes=[000051.OF,020011.OF]
                #.Fields=[NAV]
                #.Times=[20210104,20210105]
                #.Data=[[1.7652,1.7972],[1.2286,1.2511]]
                if(d.shape[0]>=2):
                    market_value=np.dot(nums,d[:,i])
                    df_returns.at[idx,'nav']=d[:,i]
                    
                ##情况2:形如下列形式，只有一只基金，有多个返回日期
                #.ErrorCode=0
                #.Codes=[000051.OF]
                #.Fields=[NAV]
                #.Times=[20210104,20210105]
                #.Data=[[1.7652,1.7972]]
                if(d.shape[0]==1 and len(list(navs.Times))>1):
                    market_value=np.dot(nums,d[0][i])
                    df_returns.at[idx,'nav']=[d[0][i]]
                    
                ##情况3，形如下列形式：多余1只基金，1个返回日期
                #.ErrorCode=0
                #.Codes=[000051.OF,020011.OF]
                #.Fields=[NAV]
                #.Times=[20210104]
                # .Data=[[1.7652,1.2286]]
                if(d.shape[0]==1 and len(list(navs.Times))==1):
                    market_value=np.dot(nums,d[0])
                    df_returns.at[idx,'nav']=d[0]
                df_returns.loc[idx,'market_value']=market_value
                i=i+1
                #if (t.strftime("%Y-%m-%d") in df_returns.index):
            ###第二个指标，基准指数，默认沪深300###        
            bench_marks=get_BenchmarkValue("000300.SH",begin_date,end_date)
            d=bench_marks.Data[0]
            i=0
            for t in bench_marks.Times:
                idx=t.strftime("%Y-%m-%d")
                bench_mark=d[i]
                df_returns.loc[idx,'bench_mark']=bench_mark
                i=i+1
        
        ###第三个指标，总资产，为每日持仓市值与资金余额相加###
        df_returns['total_assets']=df_returns.loc[:,['init_base','market_value']].sum(axis=1)
        df_returns.dropna(inplace=True)
        ###第四个指标，每日收益###
        df_returns['returns']=em.simple_returns(df_returns['total_assets'])
        ####第五个指标，每日累计收益###
        df_returns['cum_returns']=em.cum_returns(df_returns['returns'])
        ###第六个指标，最大回撤###
        max_drawdown=em.max_drawdown(df_returns['returns'])
        ###第七个指标，夏普比率###
        sharp_ratio=em.sharpe_ratio(df_returns['returns'])
        ###第八个指标，alpha及beta###
        alpha,beta=em.alpha_beta(df_returns['returns'], em.simple_returns(df_returns['bench_mark']))
        
        if(log):
            for idx in df_returns.index:
                
                market_value=df_returns.loc[idx,'market_value']
                total_assets=df_returns.loc[idx,'total_assets']
                print("回测日期为：%s,当日持仓市值为：%.2f,总资产为：%.2f"%(idx,market_value,total_assets))
                i=0
                for k,v in df_returns.loc[idx,'fund_list'].items():
                    nav=df_returns.loc[idx,'nav'][i]
                    print("持仓为：%s,数量：%.5f，该基金当日净值为：%.5f"%(k,v,nav))
                    i=i+1
        self.plot_returns(df_returns)
        
        print("策略最大回撤为：%s,夏普比率为：%.2f,策略aplha为：%.2f,beta为：%.2f"%('{:.2f}%'.format(max_drawdown*100),sharp_ratio,alpha,beta))
        return df_returns
    
    def plot_returns(self,df_returns):
        #绘制总资产图
        df_plot=df_returns.copy()
        fig = plt.figure(figsize=(30,10))
        ax = fig.add_subplot(3,1,1)
        dates = [datetime.datetime.strptime(d, "%Y-%m-%d") for d in df_returns.index]
        plt.plot(dates,df_plot.loc[:,['total_assets']],label='总资产')
        plt.ylabel('总资产(单位：元)')
        plt.title("总资产变化图")
        ax.legend()

        #绘制累计收益图
        ax = fig.add_subplot(3,1,2)
        dates = [datetime.datetime.strptime(d, "%Y-%m-%d") for d in df_returns.index]
        plt.plot(dates,df_plot.loc[:,['cum_returns']],label='累计收益')
        plt.ylabel('累计收益')
        plt.title("累计收益图")
        ax.legend()

        #比较策略收益与沪深300收益
        ax = fig.add_subplot(3,1,3)
        minmaxscaler=MinMaxScaler()
        df_plot['bench_mark']=minmaxscaler.fit_transform(df_plot[['bench_mark']])
        df_plot['total_assets']=minmaxscaler.fit_transform(df_plot[['total_assets']])
        dates = [datetime.datetime.strptime(d, "%Y-%m-%d") for d in df_returns.index]
        plt.plot(dates,df_plot.loc[:,['bench_mark']],label='沪深300指数收益')
        plt.plot(dates,df_plot.loc[:,['total_assets']],label='策略收益')
        plt.title("策略与基准收益比对")
        ax.legend()

        plt.show()
        
    