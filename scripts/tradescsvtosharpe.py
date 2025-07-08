#!/usr/bin/env python3
"""
Pairs Trading Sharpe Ratio Calculator with P&L Visualization
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sys
import warnings

warnings.filterwarnings('ignore')

def load_and_process_trades(csv_file_path):
    """Load trades CSV and process into pairs trading sessions"""
    df = pd.read_csv(csv_file_path)
    
    # Convert date columns
    df['entry_date'] = pd.to_datetime(df['entry_time'])
    df['exit_date'] = pd.to_datetime(df['exit_time'])
    df['entry_date_only'] = df['entry_date'].dt.date
    
    # Group trades by entry date to create pairs
    pairs_sessions = []
    
    for date, group in df.groupby('entry_date_only'):
        umac_trade = group[group['symbol'] == 'UMAC']
        rcat_trade = group[group['symbol'] == 'RCAT']
        
        if len(umac_trade) == 1 and len(rcat_trade) == 1:
            umac = umac_trade.iloc[0]
            rcat = rcat_trade.iloc[0]
            
            # Calculate session metrics
            total_pl = umac['entry_pl'] + rcat['entry_pl']
            total_fees = umac['exit_fees'] + rcat['exit_fees']
            net_pl = total_pl - total_fees
            
            # Calculate capital deployed
            umac_capital = abs(umac['entry_shares']) * umac['entry_price']
            rcat_capital = abs(rcat['entry_shares']) * rcat['entry_price']
            total_capital = umac_capital + rcat_capital
            
            # Calculate return
            session_return = net_pl / total_capital if total_capital > 0 else 0
            
            pairs_sessions.append({
                'date': date,
                'entry_date': umac['entry_date'],
                'exit_date': umac['exit_date'],
                'net_pl': net_pl,
                'capital_deployed': total_capital,
                'return': session_return
            })
    
    # Convert to DataFrame and sort by date
    sessions_df = pd.DataFrame(pairs_sessions)
    sessions_df = sessions_df.sort_values('entry_date').reset_index(drop=True)
    
    return sessions_df

def plot_pnl_curve(sessions_df):
    """Create P&L curve visualization"""
    # Calculate cumulative P&L
    sessions_df['cumulative_pnl'] = sessions_df['net_pl'].cumsum()
    
    # Create the plot
    plt.figure(figsize=(12, 8))
    
    # Main P&L curve
    plt.subplot(2, 1, 1)
    plt.plot(sessions_df['exit_date'], sessions_df['cumulative_pnl'], 
             linewidth=2, color='blue', label='Cumulative P&L')
    plt.fill_between(sessions_df['exit_date'], sessions_df['cumulative_pnl'], 
                     alpha=0.3, color='blue')
    
    # Add individual trade markers
    colors = ['green' if pnl > 0 else 'red' for pnl in sessions_df['net_pl']]
    plt.scatter(sessions_df['exit_date'], sessions_df['cumulative_pnl'], 
                c=colors, alpha=0.7, s=50, zorder=5)
    
    plt.title('Pairs Trading Strategy - Cumulative P&L', fontsize=14, fontweight='bold')
    plt.ylabel('Cumulative P&L ($)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Format x-axis
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=45)
    
    # Individual trade P&L
    plt.subplot(2, 1, 2)
    bar_colors = ['green' if pnl > 0 else 'red' for pnl in sessions_df['net_pl']]
    plt.bar(sessions_df['exit_date'], sessions_df['net_pl'], 
            color=bar_colors, alpha=0.7, width=5)
    
    plt.title('Individual Trade P&L', fontsize=14, fontweight='bold')
    plt.ylabel('Trade P&L ($)', fontsize=12)
    plt.xlabel('Date', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Format x-axis
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    
    # Save the plot
    plt.savefig('pairs_trading_pnl.png', dpi=300, bbox_inches='tight')
    print(f"P&L chart saved as 'pairs_trading_pnl.png'")
    
    # Show the plot
    plt.show()

def plot_drawdown_curve(sessions_df):
    """Create drawdown visualization"""
    cumulative_pnl = sessions_df['net_pl'].cumsum()
    running_max = cumulative_pnl.expanding().max()
    drawdown = running_max - cumulative_pnl
    
    plt.figure(figsize=(12, 6))
    plt.fill_between(sessions_df['exit_date'], drawdown, alpha=0.3, color='red')
    plt.plot(sessions_df['exit_date'], drawdown, color='red', linewidth=2)
    plt.title('Strategy Drawdown', fontsize=14, fontweight='bold')
    plt.ylabel('Drawdown ($)', fontsize=12)
    plt.xlabel('Date', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Format x-axis
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig('pairs_trading_drawdown.png', dpi=300, bbox_inches='tight')
    print(f"Drawdown chart saved as 'pairs_trading_drawdown.png'")
    plt.show()
    """Calculate all performance metrics"""
    returns = sessions_df['return'].values
    pnls = sessions_df['net_pl'].values
    
    # Time period
    start_date = sessions_df['entry_date'].min()
    end_date = sessions_df['exit_date'].max()
    total_days = (end_date - start_date).days
    total_years = total_days / 365.25
    
    # Basic statistics
    mean_return = np.mean(returns)
    std_return = np.std(returns, ddof=1)
    
    # Annualized metrics
    trades_per_year = len(returns) / total_years
    annualized_return = mean_return * trades_per_year
    annualized_volatility = std_return * np.sqrt(trades_per_year)
    
    # Sharpe ratio
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0
    
    # Win/Loss analysis
    winning_trades = sessions_df[sessions_df['net_pl'] > 0]
    losing_trades = sessions_df[sessions_df['net_pl'] < 0]
    win_rate = len(winning_trades) / len(sessions_df)
    
    # Profit factor
    total_wins = winning_trades['net_pl'].sum()
    total_losses = abs(losing_trades['net_pl'].sum())
    profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
    
    # Drawdown
    cumulative_pnl = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cumulative_pnl)
    drawdown = running_max - cumulative_pnl
    max_drawdown = np.max(drawdown)
    
    # Total performance
    total_pnl = pnls.sum()
    avg_capital = sessions_df['capital_deployed'].mean()
    total_return = total_pnl / avg_capital
    cagr = (1 + total_return) ** (1/total_years) - 1
    
    # Sortino ratio
    negative_returns = returns[returns < 0]
    downside_std = np.std(negative_returns, ddof=1) if len(negative_returns) > 1 else 0
    annualized_downside_std = downside_std * np.sqrt(trades_per_year)
    sortino_ratio = annualized_return / annualized_downside_std if annualized_downside_std > 0 else float('inf')
    
    return {
        'total_trades': len(sessions_df),
        'total_years': total_years,
        'total_pnl': total_pnl,
        'total_return': total_return,
        'cagr': cagr,
        'annualized_return': annualized_return,
        'annualized_volatility': annualized_volatility,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'max_drawdown_pct': max_drawdown / avg_capital,
        'avg_capital': avg_capital,
        'trades_per_year': trades_per_year
    }

def calculate_metrics(sessions_df):
    """Calculate all performance metrics"""
    returns = sessions_df['return'].values
    pnls = sessions_df['net_pl'].values
    
    # Time period
    start_date = sessions_df['entry_date'].min()
    end_date = sessions_df['exit_date'].max()
    total_days = (end_date - start_date).days
    total_years = total_days / 365.25
    
    # Basic statistics
    mean_return = np.mean(returns)
    std_return = np.std(returns, ddof=1)
    
    # Annualized metrics
    trades_per_year = len(returns) / total_years
    annualized_return = mean_return * trades_per_year
    annualized_volatility = std_return * np.sqrt(trades_per_year)
    
    # Sharpe ratio
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0
    
    # Win/Loss analysis
    winning_trades = sessions_df[sessions_df['net_pl'] > 0]
    losing_trades = sessions_df[sessions_df['net_pl'] < 0]
    win_rate = len(winning_trades) / len(sessions_df)
    
    # Profit factor
    total_wins = winning_trades['net_pl'].sum()
    total_losses = abs(losing_trades['net_pl'].sum())
    profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
    
    # Drawdown
    cumulative_pnl = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cumulative_pnl)
    drawdown = running_max - cumulative_pnl
    max_drawdown = np.max(drawdown)
    
    # Total performance
    total_pnl = pnls.sum()
    avg_capital = sessions_df['capital_deployed'].mean()
    total_return = total_pnl / avg_capital
    cagr = (1 + total_return) ** (1/total_years) - 1
    
    # Sortino ratio
    negative_returns = returns[returns < 0]
    downside_std = np.std(negative_returns, ddof=1) if len(negative_returns) > 1 else 0
    annualized_downside_std = downside_std * np.sqrt(trades_per_year)
    sortino_ratio = annualized_return / annualized_downside_std if annualized_downside_std > 0 else float('inf')
    
    return {
        'total_trades': len(sessions_df),
        'total_years': total_years,
        'total_pnl': total_pnl,
        'total_return': total_return,
        'cagr': cagr,
        'annualized_return': annualized_return,
        'annualized_volatility': annualized_volatility,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'max_drawdown_pct': max_drawdown / avg_capital,
        'avg_capital': avg_capital,
        'trades_per_year': trades_per_year
    }

def main():
    csv_file = "tradescq122.csv"
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    
    sessions_df = load_and_process_trades(csv_file)
    metrics = calculate_metrics(sessions_df)
    
    print("PAIRS TRADING PERFORMANCE METRICS")
    print("=" * 50)
    print(f"Total Trades: {metrics['total_trades']}")
    print(f"Time Period: {metrics['total_years']:.2f} years")
    print(f"Trades per Year: {metrics['trades_per_year']:.1f}")
    print()
    print("RETURN METRICS")
    print("-" * 20)
    print(f"Total P&L: ${metrics['total_pnl']:,.2f}")
    print(f"Total Return: {metrics['total_return']:.1%}")
    print(f"CAGR: {metrics['cagr']:.1%}")
    print(f"Annualized Return: {metrics['annualized_return']:.1%}")
    print()
    print("RISK METRICS")
    print("-" * 20)
    print(f"Annualized Volatility: {metrics['annualized_volatility']:.1%}")
    print(f"Maximum Drawdown: ${metrics['max_drawdown']:,.2f}")
    print(f"Max Drawdown %: {metrics['max_drawdown_pct']:.1%}")
    print()
    print("RISK-ADJUSTED METRICS")
    print("-" * 20)
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Sortino Ratio: {metrics['sortino_ratio']:.2f}")
    print()
    print("TRADING METRICS")
    print("-" * 20)
    print(f"Win Rate: {metrics['win_rate']:.1%}")
    print(f"Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"Average Capital: ${metrics['avg_capital']:,.2f}")
    print()
    
    # Generate visualizations
    print("GENERATING CHARTS")
    print("-" * 20)
    plot_pnl_curve(sessions_df)
    plot_drawdown_curve(sessions_df)

if __name__ == "__main__":
    main()