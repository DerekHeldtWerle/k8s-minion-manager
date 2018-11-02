"""The file has unit tests for the AWSBidAdvisor."""

import unittest

from cloud_provider.aws.aws_bid_advisor import AWSBidAdvisor

REFRESH_INTERVAL = 10
REGION = 'us-west-2'


class AWSBidAdvisorTest(unittest.TestCase):
    """
    Tests for AWSBidAdvisor.
    """
    def test_ba_lifecycle(self):
        """
        Tests that the AWSBidVisor starts threads and stops them correctly.
        """
        bidadv = AWSBidAdvisor(REFRESH_INTERVAL, REFRESH_INTERVAL, REGION)
        assert len(bidadv.all_bid_advisor_threads) == 0
        bidadv.run()
        assert len(bidadv.all_bid_advisor_threads) == 2
        bidadv.shutdown()
        assert len(bidadv.all_bid_advisor_threads) == 0

    def test_ba_on_demand_pricing(self):
        """
        Tests that the AWSBidVisor correctly gets the on-demand pricing.
        """
        bidadv = AWSBidAdvisor(REFRESH_INTERVAL, REFRESH_INTERVAL, REGION)
        assert len(bidadv.on_demand_price_dict) == 0
        updater = bidadv.OnDemandUpdater(bidadv)
        updater.get_on_demand_pricing()
        assert len(bidadv.on_demand_price_dict) > 0

    def test_ba_spot_pricing(self):
        """
        Tests that the AWSBidVisor correctly gets the spot instance pricing.
        """
        bidadv = AWSBidAdvisor(REFRESH_INTERVAL, REFRESH_INTERVAL, REGION)
        assert len(bidadv.spot_price_list) == 0
        updater = bidadv.SpotInstancePriceUpdater(bidadv)
        updater.get_spot_price_info()
        assert len(bidadv.spot_price_list) > 0

    def test_ba_price_update(self):
        """
        Tests that the AXBidVisor actually updates the pricing info.
        """
        bidadv = AWSBidAdvisor(REFRESH_INTERVAL, REFRESH_INTERVAL, REGION)
        od_updater = bidadv.OnDemandUpdater(bidadv)
        od_updater.get_on_demand_pricing()

        sp_updater = bidadv.SpotInstancePriceUpdater(bidadv)
        sp_updater.get_spot_price_info()

        # Verify that the pricing info was populated.
        assert len(bidadv.on_demand_price_dict) > 0
        assert len(bidadv.spot_price_list) > 0

        # Make the price dicts empty to check if they get updated.
        bidadv.on_demand_price_dict = {}
        bidadv.spot_price_list = {}

        od_updater.get_on_demand_pricing()
        sp_updater.get_spot_price_info()

        # Verify that the pricing info is populated again.
        assert len(bidadv.on_demand_price_dict) > 0
        assert len(bidadv.spot_price_list) > 0

    def test_ba_get_bid(self):
        """
        Tests that the bid_advisor's get_new_bid() method returns correct
        bid information.
        """
        bidadv = AWSBidAdvisor(REFRESH_INTERVAL, REFRESH_INTERVAL, REGION)

        instance_type = "m3.large"
        zones = ["us-west-2b"]
        # Manually populate the prices so that spot-instance prices are chosen.
        bidadv.on_demand_price_dict["m3.large"] = "100"
        bidadv.spot_price_list = [{'InstanceType': instance_type,
                                   'SpotPrice': '80',
                                   'AvailabilityZone': "us-west-2b"}]
        bid_info = bidadv.get_new_bid(zones, instance_type)
        assert bid_info is not None, "BidAdvisor didn't return any " + \
            "now bid information."
        assert bid_info["type"] == "spot"
        assert isinstance(bid_info["price"], str)

        # Manually populate the prices so that on-demand instances are chosen.
        bidadv.spot_price_list = [{'InstanceType': instance_type,
                                   'SpotPrice': '85',
                                   'AvailabilityZone': "us-west-2b"}]
        bid_info = bidadv.get_new_bid(zones, instance_type)
        assert bid_info is not None, "BidAdvisor didn't return any now " + \
            "bid information."
        assert bid_info["type"] == "on-demand"

    def test_ba_get_bid_no_data(self):
        """
        Tests that the BidAdvisor returns the default if the pricing
        information hasn't be obtained yet.
        """
        bidadv = AWSBidAdvisor(REFRESH_INTERVAL, REFRESH_INTERVAL, REGION)
        bid_info = bidadv.get_new_bid(['us-west-2a'], 'm3.large')
        assert bid_info["type"] == "on-demand"

    def test_ba_get_current_price(self):
        """
        Tests that the BidAdvisor returns the most recent price information.
        """
        bidadv = AWSBidAdvisor(REFRESH_INTERVAL, REFRESH_INTERVAL, REGION)

        od_updater = bidadv.OnDemandUpdater(bidadv)
        od_updater.get_on_demand_pricing()

        sp_updater = bidadv.SpotInstancePriceUpdater(bidadv)
        sp_updater.get_spot_price_info()

        # Verify that the pricing info was populated.
        assert len(bidadv.on_demand_price_dict) > 0
        assert len(bidadv.spot_price_list) > 0

        price_info_map = bidadv.get_current_price()
        assert price_info_map["spot"] is not None
        assert price_info_map["on-demand"] is not None

    def test_ba_parse_row(self):
        """
        Tests that the BidAdvisor parses the rows in on-demand price information.
        """
        bidadv = AWSBidAdvisor(REFRESH_INTERVAL, REFRESH_INTERVAL, REGION)

        od_updater = bidadv.OnDemandUpdater(bidadv)
        row = {}
        row['RateCode'] = "JRTCKXETXF.6YS6EN2CT7"
        row["TermType"] = "OnDemand"
        row["PriceDescription"] = "On Demand Linux"
        row["Location"] = "US West (Oregon)"
        row["Operating System"] = "Linux"
        row["Pre Installed S/W"] = "NA"
        row["Tenancy"] = "Shared"
        row["PricePerUnit"] = "0.453"
        row["Instance Type"] = "m5.4xlarge"

        od_updater.parse_price_row(row)
        assert od_updater.bid_advisor.on_demand_price_dict['m5.4xlarge'] == "0.453"

        od_updater.parse_price_row(row)
        assert od_updater.bid_advisor.on_demand_price_dict['m5.4xlarge'] == "0.453"

        row["PricePerUnit"] = "0.658"
        od_updater.parse_price_row(row)
        assert od_updater.bid_advisor.on_demand_price_dict['m5.4xlarge'] == "0.658"

        row["PricePerUnit"] = "0.00"
        od_updater.parse_price_row(row)
        assert od_updater.bid_advisor.on_demand_price_dict['m5.4xlarge'] == "0.658"

        row['RateCode'] = "Some Random RateCode"
        od_updater.parse_price_row(row)
