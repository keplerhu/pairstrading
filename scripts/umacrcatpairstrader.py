from cloudquant.interfaces import Strategy
import numpy as np

class UMACRCATPairsStrategy(Strategy):
    
    # Class variables shared between all instances
    _last_processed_date = None
    _shared_positions = {'umac': 0, 'rcat': 0, 'in_trade': False, 'trade_direction': None}
    _execution_lock = False  # Prevent multiple simultaneous executions
    
    def __init__(self):
        # Strategy parameters
        self.hedge_ratio = 1.389508  # UMAC shares per RCAT share
        self.lookback_period = 20    # Days for calculating spread statistics
        self.entry_threshold = 1.4   # Z-score threshold for entry
        self.exit_threshold = 0.2    # Z-score threshold for exit
        self.max_position_size = 1000  # Maximum shares per leg

    @classmethod
    def is_symbol_qualified(cls, symbol, md, service, account):
        # Only trade UMAC and RCAT
        return symbol in ['UMAC', 'RCAT']

    def on_start(self, md, order, service, account):
      
        # Only the RCAT instance will coordinate execution to avoid duplication
        if self.symbol == 'RCAT':
            # Schedule daily update one minute before market close
            close_time_minus_1min = md.market_close_time - service.time_interval(minutes=1)
            service.add_time_trigger(close_time_minus_1min, timer_id='daily_pairs_update')

    def on_timer(self, event, md, order, service, account):
        """Handle timer events for daily updates - only RCAT instance coordinates"""
        if event.timer_id == 'daily_pairs_update' and self.symbol == 'RCAT':
            current_date = event.timestamp.date() if hasattr(event.timestamp, 'date') else str(event.timestamp)[:10]
            
            # Only process if we haven't done so today and no other execution is in progress
            if (UMACRCATPairsStrategy._last_processed_date != current_date and 
                not UMACRCATPairsStrategy._execution_lock):
                
                UMACRCATPairsStrategy._execution_lock = True
                
                try:
                    # Execute trading logic with direct data access
                    self.execute_pairs_trading_logic(md, order, service, account)
                    UMACRCATPairsStrategy._last_processed_date = current_date
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                finally:
                    UMACRCATPairsStrategy._execution_lock = False
                    
                # Only reschedule if we actually processed today
                close_time_minus_1min = md.market_close_time - service.time_interval(minutes=1)
                service.add_time_trigger(close_time_minus_1min, timer_id='daily_pairs_update')
            else:
                if UMACRCATPairsStrategy._last_processed_date == current_date:
                if UMACRCATPairsStrategy._execution_lock:

    def execute_pairs_trading_logic(self, md, order, service, account):
        """Execute pairs trading logic using Z-scores with direct data access"""
        
        try:
            # Get UMAC data directly
            umac_bars = md['UMAC'].bar.daily(start=-self.lookback_period)
            if umac_bars is None or len(umac_bars.close) < self.lookback_period:
                return
            
            umac_prices = list(umac_bars.close)
            umac_current_price = umac_prices[-1]
            
            # Try to get current UMAC L1 price
            try:
                umac_l1_price = md['UMAC'].l1.last()
                if umac_l1_price is not None and umac_l1_price > 0:
                    umac_current_price = umac_l1_price
                
            # Get RCAT data directly
            rcat_bars = md['RCAT'].bar.daily(start=-self.lookback_period)
            if rcat_bars is None or len(rcat_bars.close) < self.lookback_period:
                return
            
            rcat_prices = list(rcat_bars.close)
            rcat_current_price = rcat_prices[-1]
            
            # Try to get current RCAT L1 price
            try:
                rcat_l1_price = md['RCAT'].l1.last()
                if rcat_l1_price is not None and rcat_l1_price > 0:
                    rcat_current_price = rcat_l1_price
                
        except Exception as e:
            return
        
        # Ensure we have equal length data
        min_length = min(len(umac_prices), len(rcat_prices))
        if min_length < self.lookback_period:
            return
        
        # Use the most recent data of equal length
        umac_recent = umac_prices[-min_length:]
        rcat_recent = rcat_prices[-min_length:]
        
        # Calculate historical spreads
        spread_history = []
        for i in range(min_length):
            spread = umac_recent[i] - (self.hedge_ratio * rcat_recent[i])
            spread_history.append(spread)
        
        # Calculate current spread
        current_spread = umac_current_price - (self.hedge_ratio * rcat_current_price)
        
        # Calculate spread statistics
        spread_mean = np.mean(spread_history)
        spread_std = np.std(spread_history)
        
        if spread_std == 0:
            return
        
        # Calculate Z-score
        z_score = (current_spread - spread_mean) / spread_std
        
     
        # Trading logic
        if not UMACRCATPairsStrategy._shared_positions['in_trade']:
            self.check_entry_signals(z_score, umac_current_price, rcat_current_price, md, order, service, account)
        else:
            self.check_exit_signals(z_score, md, order, service, account)

    def check_entry_signals(self, z_score, umac_current_price, rcat_current_price, md, order, service, account):
        """Check for entry signals"""
        
        if z_score > self.entry_threshold:
            # Spread is high - short the spread (short UMAC, long RCAT)
            self.enter_short_spread(umac_current_price, rcat_current_price, md, order, service, account)
            
        elif z_score < -self.entry_threshold:
            # Spread is low - long the spread (long UMAC, short RCAT)
            self.enter_long_spread(umac_current_price, rcat_current_price, md, order, service, account)

    def check_exit_signals(self, z_score, md, order, service, account):
        """Check for exit signals"""
        
        should_exit = False
        
        if UMACRCATPairsStrategy._shared_positions['trade_direction'] == 'long_spread' and z_score > -self.exit_threshold:
            should_exit = True
        elif UMACRCATPairsStrategy._shared_positions['trade_direction'] == 'short_spread' and z_score < self.exit_threshold:
            should_exit = True
        
        if should_exit:
            self.close_positions(md, order, service, account)

    def enter_long_spread(self, umac_current_price, rcat_current_price, md, order, service, account):
        """Enter long spread position: Long UMAC, Short RCAT"""
        
        current_umac = float(umac_current_price)
        current_rcat = float(rcat_current_price)
        
        
        # Calculate position sizes based on available capital
        available_capital = float(account.buying_power) / 2.0  # Split between two legs
        umac_shares = min(self.max_position_size, int(available_capital / current_umac))
        rcat_shares = int(umac_shares * self.hedge_ratio)
        
        
        if umac_shares > 0 and rcat_shares > 0:
            
            try:
                # Long UMAC
                order.algo_buy(symbol='UMAC', 
                             algorithm='{1f9b553d-30bf-40a3-8868-ebe70b5079b2}', 
                             intent='init',
                             order_quantity=umac_shares)
                
                # Short RCAT  
                order.algo_sell(symbol='RCAT', 
                              algorithm='{5fc61945-3498-47da-abf6-b5dabdc9f4ac}', 
                              intent='init',
                              order_quantity=rcat_shares)
                
                # Update shared position tracking
                UMACRCATPairsStrategy._shared_positions['umac'] = umac_shares
                UMACRCATPairsStrategy._shared_positions['rcat'] = -rcat_shares
                UMACRCATPairsStrategy._shared_positions['in_trade'] = True
                UMACRCATPairsStrategy._shared_positions['trade_direction'] = 'long_spread'
                
                
            except Exception as e:
                import traceback
                traceback.print_exc()

    def enter_short_spread(self, umac_current_price, rcat_current_price, md, order, service, account):
        """Enter short spread position: Short UMAC, Long RCAT"""
        
        current_umac = float(umac_current_price)
        current_rcat = float(rcat_current_price)
        
        # Calculate position sizes
        available_capital = float(account.buying_power) / 2
        umac_shares = min(self.max_position_size, int(available_capital / current_umac))
        rcat_shares = int(float(umac_shares) * self.hedge_ratio)
        
        if umac_shares > 0 and rcat_shares > 0:
            
            try:
                # Short UMAC
                order.algo_sell(symbol='UMAC', 
                              algorithm='{5fc61945-3498-47da-abf6-b5dabdc9f4ac}', 
                              intent='init',
                              order_quantity=int(umac_shares))
                
                # Long RCAT
                order.algo_buy(symbol='RCAT', 
                             algorithm='{1f9b553d-30bf-40a3-8868-ebe70b5079b2}', 
                             intent='init',
                             order_quantity=int(rcat_shares))
                
                # Update shared position tracking
                UMACRCATPairsStrategy._shared_positions['umac'] = -umac_shares
                UMACRCATPairsStrategy._shared_positions['rcat'] = rcat_shares
                UMACRCATPairsStrategy._shared_positions['in_trade'] = True
                UMACRCATPairsStrategy._shared_positions['trade_direction'] = 'short_spread'
                
                
            

    def close_positions(self, md, order, service, account):
        """Close all positions"""
        
        try:
            umac_pos = UMACRCATPairsStrategy._shared_positions['umac']
            rcat_pos = UMACRCATPairsStrategy._shared_positions['rcat']
            
            # Close UMAC position
            if umac_pos > 0:
                order.algo_sell(symbol='UMAC', 
                              algorithm='{5fc61945-3498-47da-abf6-b5dabdc9f4ac}', 
                              intent='exit')
            elif umac_pos < 0:
                order.algo_buy(symbol='UMAC', 
                             algorithm='{1f9b553d-30bf-40a3-8868-ebe70b5079b2}', 
                             intent='exit')
            
            # Close RCAT position
            if rcat_pos > 0:
                order.algo_sell(symbol='RCAT', 
                              algorithm='{5fc61945-3498-47da-abf6-b5dabdc9f4ac}', 
                              intent='exit')
            elif rcat_pos < 0:
                order.algo_buy(symbol='RCAT', 
                             algorithm='{1f9b553d-30bf-40a3-8868-ebe70b5079b2}', 
                             intent='exit')
            
            # Reset shared positions
            UMACRCATPairsStrategy._shared_positions = {'umac': 0, 'rcat': 0, 'in_trade': False, 'trade_direction': None}
            
            
        
    def on_fill(self, event, md, order, service, account):
        """Handle order fills and update position tracking"""
        fill_qty = event.shares
        fill_price = event.price
        symbol = self.symbol
        side = event.actual_direction
        