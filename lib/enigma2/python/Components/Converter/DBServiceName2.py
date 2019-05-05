
from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceReference, eServiceCenter, eTimer, getBestPlayableServiceReference
from Components.Element import cached
from Components.config import config
import NavigationInstance
try:
    from Components.Renderer.ChannelNumber import ChannelNumberClasses
    correctChannelNumber = True
except:
    correctChannelNumber = False

class DBServiceName2(Converter, object):
    NAME = 0
    NUMBER = 1
    BOUQUET = 2
    PROVIDER = 3
    REFERENCE = 4
    ORBPOS = 5
    TPRDATA = 6
    SATELLITE = 7
    ALLREF = 8
    FORMAT = 9

    def __init__(self, type):
        Converter.__init__(self, type)
        if type == 'Name' or not len(str(type)):
            self.type = self.NAME
        else:
            if type == 'Number':
                self.type = self.NUMBER
            else:
                if type == 'Bouquet':
                    self.type = self.BOUQUET
                else:
                    if type == 'Provider':
                        self.type = self.PROVIDER
                    else:
                        if type == 'Reference':
                            self.type = self.REFERENCE
                        else:
                            if type == 'OrbitalPos':
                                self.type = self.ORBPOS
                            else:
                                if type == 'TpansponderInfo':
                                    self.type = self.TPRDATA
                                else:
                                    if type == 'Satellite':
                                        self.type = self.SATELLITE
                                    else:
                                        if type == 'AllRef':
                                            self.type = self.ALLREF
                                        else:
                                            self.type = self.FORMAT
                                            self.sfmt = type[:]
        try:
            if (self.type == 1 or self.type == 9 and '%n' in self.sfmt) and correctChannelNumber:
                ChannelNumberClasses.append(self.forceChanged)
        except:
            pass

        self.refstr = self.isStream = self.ref = self.info = self.what = self.tpdata = None
        self.Timer = eTimer()
        self.Timer.callback.append(self.neededChange)
        self.IPTVcontrol = self.isAdditionalService(type=0)
        self.AlternativeControl = self.isAdditionalService(type=1)
        return

    def isAdditionalService(self, type=0):

        def searchService(serviceHandler, bouquet):
            istype = False
            servicelist = serviceHandler.list(bouquet)
            if servicelist is not None:
                while True:
                    s = servicelist.getNext()
                    if not s.valid():
                        break
                    if not s.flags & (eServiceReference.isMarker | eServiceReference.isDirectory):
                        if type:
                            if s.flags & eServiceReference.isGroup:
                                istype = True
                                return istype
                        else:
                            if '%3a//' in s.toString().lower():
                                istype = True
                                return istype

            return istype

        isService = False
        serviceHandler = eServiceCenter.getInstance()
        if not config.usage.multibouquet.value:
            service_types_tv = '1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 22) || (type == 25) || (type == 134) || (type == 195)'
            rootstr = '%s FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet' % service_types_tv
        else:
            rootstr = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
        bouquet = eServiceReference(rootstr)
        if not config.usage.multibouquet.value:
            isService = searchService(serviceHandler, bouquet)
        else:
            bouquetlist = serviceHandler.list(bouquet)
            if bouquetlist is not None:
                while True:
                    bouquet = bouquetlist.getNext()
                    if not bouquet.valid():
                        break
                    if bouquet.flags & eServiceReference.isDirectory:
                        isService = searchService(serviceHandler, bouquet)
                        if isService:
                            break

        return isService

    def getServiceNumber(self, ref):

        def searchHelper(serviceHandler, num, bouquet):
            servicelist = serviceHandler.list(bouquet)
            if servicelist is not None:
                while True:
                    s = servicelist.getNext()
                    if not s.valid():
                        break
                    if not s.flags & (eServiceReference.isMarker | eServiceReference.isDirectory):
                        num += 1
                        if s == ref:
                            return (s, num)

            return (
             None, num)

        if isinstance(ref, eServiceReference):
            isRadioService = ref.getData(0) in (2, 10)
            lastpath = isRadioService and config.radio.lastroot.value or config.tv.lastroot.value
            if 'FROM BOUQUET' not in lastpath:
                if 'FROM PROVIDERS' in lastpath:
                    return ('P', _('Provider'))
                if 'FROM SATELLITES' in lastpath:
                    return ('S', _('Satellites'))
                if ') ORDER BY name' in lastpath:
                    return ('A', _('All Services'))
                return (0, 'N/A')
            try:
                acount = config.plugins.NumberZapExt.enable.value and config.plugins.NumberZapExt.acount.value or config.usage.alternative_number_mode.value
            except:
                acount = False

            rootstr = ''
            for x in lastpath.split(';'):
                if x != '':
                    rootstr = x

            serviceHandler = eServiceCenter.getInstance()
            if acount is True or not config.usage.multibouquet.value:
                bouquet = eServiceReference(rootstr)
                service, number = searchHelper(serviceHandler, 0, bouquet)
            else:
                if isRadioService:
                    bqrootstr = '1:7:2:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.radio" ORDER BY bouquet'
                else:
                    bqrootstr = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
                number = 0
                cur = eServiceReference(rootstr)
                bouquet = eServiceReference(bqrootstr)
                bouquetlist = serviceHandler.list(bouquet)
                if bouquetlist is not None:
                    while True:
                        bouquet = bouquetlist.getNext()
                        if not bouquet.valid():
                            break
                        if bouquet.flags & eServiceReference.isDirectory:
                            service, number = searchHelper(serviceHandler, number, bouquet)
                            if service is not None and cur == bouquet:
                                break

                if service is not None:
                    info = serviceHandler.info(bouquet)
                    name = info and info.getName(bouquet) or ''
                    return (
                     number, name)
        return (0, '')

    def getProviderName(self, ref):
        if isinstance(ref, eServiceReference):
            from Screens.ChannelSelection import service_types_radio, service_types_tv
            typestr = ref.getData(0) in (2, 10) and service_types_radio or service_types_tv
            pos = typestr.rfind(':')
            rootstr = '%s (channelID == %08x%04x%04x) && %s FROM PROVIDERS ORDER BY name' % (typestr[:pos + 1], ref.getUnsignedData(4), ref.getUnsignedData(2), ref.getUnsignedData(3), typestr[pos + 1:])
            provider_root = eServiceReference(rootstr)
            serviceHandler = eServiceCenter.getInstance()
            providerlist = serviceHandler.list(provider_root)
            if providerlist is not None:
                while True:
                    provider = providerlist.getNext()
                    if not provider.valid():
                        break
                    if provider.flags & eServiceReference.isDirectory:
                        servicelist = serviceHandler.list(provider)
                        if servicelist is not None:
                            while True:
                                service = servicelist.getNext()
                                if not service.valid():
                                    break
                                if service == ref:
                                    info = serviceHandler.info(provider)
                                    return info and info.getName(provider) or 'Unknown'

        return ''

    def getTransponderInfo(self, info, ref, fmt):
        result = ''
        if self.tpdata is None:
            if ref:
                self.tpdata = ref and info.getInfoObject(ref, iServiceInformation.sTransponderData)
            else:
                self.tpdata = info.getInfoObject(iServiceInformation.sTransponderData)
            if not isinstance(self.tpdata, dict):
                self.tpdata = None
                return result
        if self.isStream:
            type = 'IP-TV'
        else:
            type = self.tpdata.get('tuner_type', '')
        if not fmt or fmt == 'T':
            if type == 'DVB-C':
                fmt = [
                 't ', 'F ', 'Y ', 'i ', 'f ', 'M']
            elif type == 'DVB-T':
                if ref:
                    fmt = [
                     'O ', 'F ', 'c ', 'l ', 'h ', 'm ', 'g ']
                else:
                    fmt = [
                     't ', 'F ', 'c ', 'l ', 'h ', 'm ', 'g ']
            else:
                if type == 'IP-TV':
                    return _('Streaming')
                fmt = ['O ', 's ', 'M ', 'F ', 'p ', 'Y ', 'f']
        for line in fmt:
            f = line[:1]
            if f == 't':
                if type == 'DVB-S':
                    result += _('Satellite')
                elif type == 'DVB-C':
                    result += _('Cable')
                elif type == 'DVB-T':
                    result += _('Terrestrial')
                elif type == 'IP-TV':
                    result += _('Stream-tv')
                else:
                    result += 'N/A'
            else:
                if f == 's':
                    if type == 'DVB-S':
                        x = self.tpdata.get('system', 0)
                        result += x in range(2) and {0: 'DVB-S', 1: 'DVB-S2'}[x] or ''
                    else:
                        result += type
                else:
                    if f == 'F':
                        if type in ('DVB-S', 'DVB-C') and self.tpdata.get('frequency', 0) > 0:
                            result += '%d MHz' % (self.tpdata.get('frequency', 0) / 1000)
                        if type in 'DVB-T':
                            result += '%.3f MHz' % ((self.tpdata.get('frequency', 0) + 500) / 1000 / 1000.0)
                    else:
                        if f == 'f':
                            if type in ('DVB-S', 'DVB-C'):
                                x = self.tpdata.get('fec_inner', 15)
                                result += x in range(10) + [15] and {0: 'Auto', 1: '1/2', 2: '2/3', 3: '3/4', 4: '5/6', 5: '7/8', 6: '8/9', 7: '3/5', 8: '4/5', 9: '9/10', 15: 'None'}[x] or ''
                            elif type == 'DVB-T':
                                x = self.tpdata.get('code_rate_lp', 5)
                                result += x in range(6) and {0: '1/2', 1: '2/3', 2: '3/4', 3: '5/6', 4: '7/8', 5: 'Auto'}[x] or ''
                        else:
                            if f == 'i':
                                if type in ('DVB-S', 'DVB-C', 'DVB-T'):
                                    x = self.tpdata.get('inversion', 2)
                                    result += x in range(3) and {0: 'On', 1: 'Off', 2: 'Auto'}[x] or ''
                            else:
                                if f == 'O':
                                    if type == 'DVB-S':
                                        x = self.tpdata.get('orbital_position', 0)
                                        result += x > 1800 and '%d.%d\xc2\xb0W' % ((3600 - x) / 10, (3600 - x) % 10) or '%d.%d\xc2\xb0E' % (x / 10, x % 10)
                                    elif type == 'DVB-T':
                                        result += 'DVB-T'
                                    elif type == 'DVB-C':
                                        result += 'DVB-C'
                                    elif type == 'Iptv':
                                        result += 'Stream'
                                else:
                                    if f == 'M':
                                        x = self.tpdata.get('modulation', 1)
                                        if type == 'DVB-S':
                                            result += x in range(4) and {0: 'Auto', 1: 'QPSK', 2: '8PSK', 3: 'QAM16'}[x] or ''
                                        elif type == 'DVB-C':
                                            result += x in range(6) and {0: 'Auto', 1: 'QAM16', 2: 'QAM32', 3: 'QAM64', 4: 'QAM128', 5: 'QAM256'}[x] or ''
                                    else:
                                        if f == 'p':
                                            if type == 'DVB-S':
                                                x = self.tpdata.get('polarization', 0)
                                                result += x in range(4) and {0: 'H', 1: 'V', 2: 'LHC', 3: 'RHC'}[x] or '?'
                                        else:
                                            if f == 'Y':
                                                if type in ('DVB-S', 'DVB-C'):
                                                    result += '%d' % (self.tpdata.get('symbol_rate', 0) / 1000)
                                            else:
                                                if f == 'r':
                                                    if not self.isStream:
                                                        x = self.tpdata.get('rolloff')
                                                        if x is not None:
                                                            result += x in range(3) and {0: '0.35', 1: '0.25', 2: '0.20'}[x] or ''
                                                else:
                                                    if f == 'o':
                                                        if not self.isStream:
                                                            x = self.tpdata.get('pilot')
                                                            if x is not None:
                                                                result += x in range(3) and {0: 'Off', 1: 'On', 2: 'Auto'}[x] or ''
                                                    else:
                                                        if f == 'c':
                                                            if type == 'DVB-T':
                                                                x = self.tpdata.get('constellation', 3)
                                                                result += x in range(4) and {0: 'QPSK', 1: 'QAM16', 2: 'QAM64', 3: 'Auto'}[x] or ''
                                                        else:
                                                            if f == 'l':
                                                                if type == 'DVB-T':
                                                                    x = self.tpdata.get('code_rate_lp', 5)
                                                                    result += x in range(6) and {0: '1/2', 1: '2/3', 2: '3/4', 3: '5/6', 4: '7/8', 5: 'Auto'}[x] or ''
                                                            else:
                                                                if f == 'h':
                                                                    if type == 'DVB-T':
                                                                        x = self.tpdata.get('code_rate_hp', 5)
                                                                        result += x in range(6) and {0: '1/2', 1: '2/3', 2: '3/4', 3: '5/6', 4: '7/8', 5: 'Auto'}[x] or ''
                                                                else:
                                                                    if f == 'm':
                                                                        if type == 'DVB-T':
                                                                            x = self.tpdata.get('transmission_mode', 2)
                                                                            result += x in range(3) and {0: '2k', 1: '8k', 2: 'Auto'}[x] or ''
                                                                    else:
                                                                        if f == 'g':
                                                                            if type == 'DVB-T':
                                                                                x = self.tpdata.get('guard_interval', 4)
                                                                                result += x in range(5) and {0: '1/32', 1: '1/16', 2: '1/8', 3: '1/4', 4: 'Auto'}[x] or ''
                                                                        else:
                                                                            if f == 'b':
                                                                                if type == 'DVB-T':
                                                                                    x = self.tpdata.get('bandwidth', 1)
                                                                                    result += x in range(4) and {0: '8 MHz', 1: '7 MHz', 2: '6 MHz', 3: 'Auto'}[x] or ''
                                                                            else:
                                                                                if f == 'e':
                                                                                    if type == 'DVB-T':
                                                                                        x = self.tpdata.get('hierarchy_information', 4)
                                                                                        result += x in range(5) and {0: 'None', 1: '1', 2: '2', 3: '4', 4: 'Auto'}[x] or ''
            result += line[1:]

        return result

    def getSatelliteName(self, ref):
        if isinstance(ref, eServiceReference):
            orbpos = ref.getUnsignedData(4) >> 16
            if orbpos == 65535:
                return _('Cable')
            if orbpos == 61166:
                return _('Terrestrial')
            orbpos = ref.getData(4) >> 16
            if orbpos < 0:
                orbpos += 3600
            try:
                from Components.NimManager import nimmanager
                return str(nimmanager.getSatDescription(orbpos))
            except:
                dir = ref.flags & (eServiceReference.isDirectory | eServiceReference.isMarker)
                if not dir:
                    refString = ref.toString().lower()
                    if refString.startswith('-1'):
                        return ''
                    if refString.startswith('1:134:'):
                        return _('Alternative')
                    if refString.startswith('4097:'):
                        return _('Internet')
                    return orbpos > 1800 and '%d.%d\xc2\xb0W' % ((3600 - orbpos) / 10, (3600 - orbpos) % 10) or '%d.%d\xc2\xb0E' % (orbpos / 10, orbpos % 10)

        return ''

    def getIPTVProvider(self, refstr):
        if 'tvshka' in refstr:
            return 'SCHURA'
        if 'udp/239.0.1' in refstr:
            return 'Lanet'
        if '3a7777' in refstr:
            return 'IPTVNTV'
        if 'KartinaTV' in refstr:
            return 'KartinaTV'
        if 'Megaimpuls' in refstr:
            return 'MEGAIMPULSTV'
        if 'Newrus' in refstr:
            return 'NEWRUSTV'
        if 'Sovok' in refstr:
            return 'SOVOKTV'
        if 'Rodnoe' in refstr:
            return 'RODNOETV'
        if '238.1.1.89%3a1234' in refstr:
            return 'TRK UKRAINE'
        if '238.1.1.181%3a1234' in refstr:
            return 'VIASAT'
        if 'cdnet' in refstr:
            return 'NonameTV'
        if 'unicast' in refstr:
            return 'StarLink'
        if 'udp/239.255.2.' in refstr:
            return 'Planeta'
        if 'udp/233.7.70.' in refstr:
            return 'Rostelecom'
        if 'udp/239.1.1.' in refstr:
            return 'Real'
        if 'udp/238.0.' in refstr or 'udp/233.191.' in refstr:
            return 'Triolan'
        if '%3a8208' in refstr:
            return 'MOVISTAR+'
        if 'udp/239.0.0.' in refstr:
            return 'Trinity'
        if '.cn.ru' in refstr or 'novotelecom' in refstr:
            return 'Novotelecom'
        if 'www.youtube.com' in refstr:
            return 'www.youtube.com'
        if '.torrent-tv.ru' in refstr:
            return 'torrent-tv.ru'
        if 'web.tvbox.md' in refstr:
            return 'web.tvbox.md'
        if 'live-p12' in refstr:
            return 'PAC12'
        if '4097' in refstr:
            return 'StreamTV'
        if '%3a1234' in refstr:
            return 'IPTV1'
        return ''

    def getPlayingref(self, ref):
        playingref = None
        if NavigationInstance.instance:
            playingref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
        if not playingref:
            playingref = eServiceReference()
        return playingref

    def resolveAlternate(self, ref):
        nref = getBestPlayableServiceReference(ref, self.getPlayingref(ref))
        if not nref:
            nref = getBestPlayableServiceReference(ref, eServiceReference(), True)
        return nref

    def getReferenceType(self, refstr, ref):
        if ref is None:
            if NavigationInstance.instance:
                playref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
                if playref:
                    refstr = playref.toString() or ''
                    prefix = ''
                    if refstr.startswith('4097:'):
                        prefix += 'GStreamer '
                    if '%3a//' in refstr:
                        sref = (' ').join(refstr.split(':')[10:])
                        refstr = prefix + sref
                    else:
                        sref = (':').join(refstr.split(':')[:10])
                        refstr = prefix + sref
        else:
            if refstr != '':
                prefix = ''
                if refstr.startswith('1:7:'):
                    if 'FROM BOUQUET' in refstr:
                        prefix += 'Bouquet '
                    elif '(provider == ' in refstr:
                        prefix += 'Provider '
                    elif '(satellitePosition == ' in refstr:
                        prefix += 'Satellit '
                    elif '(channelID == ' in refstr:
                        prefix += 'Current tr '
                else:
                    if refstr.startswith('1:134:'):
                        prefix += 'Alter '
                    else:
                        if refstr.startswith('1:64:'):
                            prefix += 'Marker '
                        else:
                            if refstr.startswith('4097:'):
                                prefix += 'GStreamer '
                    if self.isStream:
                        if self.refstr:
                            if '%3a//' in self.refstr:
                                sref = (' ').join(self.refstr.split(':')[10:])
                            else:
                                sref = (':').join(self.refstr.split(':')[:10])
                        else:
                            sref = (' ').join(refstr.split(':')[10:])
                        return prefix + sref
                if self.refstr:
                    sref = (':').join(self.refstr.split(':')[:10])
                else:
                    sref = (':').join(refstr.split(':')[:10])
                return prefix + sref
        return refstr

    @cached
    def getText(self):
        service = self.source.service
        if isinstance(service, iPlayableServicePtr):
            info = service and service.info()
            ref = None
        else:
            info = service and self.source.info
            ref = service
        if not info:
            return ''
        if ref:
            refstr = ref.toString()
        else:
            refstr = info.getInfoString(iServiceInformation.sServiceref)
        if refstr is None:
            refstr = ''
        if self.AlternativeControl:
            if ref and refstr.startswith('1:134:') and self.ref is None:
                nref = self.resolveAlternate(ref)
                if nref:
                    self.ref = nref
                    self.info = eServiceCenter.getInstance().info(self.ref)
                    self.refstr = self.ref.toString()
                    if not self.info:
                        return ''
        if self.IPTVcontrol:
            if '%3a//' in refstr or self.refstr and '%3a//' in self.refstr or refstr.startswith('4097:'):
                self.isStream = True
        if self.type == self.NAME:
            name = ref and (info.getName(ref) or 'N/A') or info.getName() or 'N/A'
            prefix = ''
            if self.ref:
                prefix = ' (alter)'
            name += prefix
            return name.replace('\xc2\x86', '').replace('\xc2\x87', '')
        if self.type == self.NUMBER:
            try:
                service = self.source.serviceref
                num = service and service.getChannelNum() or None
            except:
                num = None
            else:
                if num:
                    return str(num)

            num, bouq = self.getServiceNumber(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
            return num and str(num) or ''
        else:
            if self.type == self.BOUQUET:
                num, bouq = self.getServiceNumber(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
                return bouq
            if self.type == self.PROVIDER:
                if self.isStream:
                    if self.refstr and ('%3a//' in self.refstr or '%3a//' in self.refstr):
                        return self.getIPTVProvider(self.refstr)
                    return self.getIPTVProvider(refstr)
                if self.ref:
                    return self.getProviderName(self.ref)
                if ref:
                    return self.getProviderName(ref)
                return info.getInfoString(iServiceInformation.sProvider) or ''
            else:
                if self.type == self.REFERENCE:
                    if self.refstr:
                        return self.refstr
                    return refstr
                if self.type == self.ORBPOS:
                    if self.isStream:
                        return 'Stream'
                    if self.ref and self.info:
                        return self.getTransponderInfo(self.info, self.ref, 'O')
                    return self.getTransponderInfo(info, ref, 'O')
                else:
                    if self.type == self.TPRDATA:
                        if self.isStream:
                            return _('Streaming')
                        if self.ref and self.info:
                            return self.getTransponderInfo(self.info, self.ref, 'T')
                        return self.getTransponderInfo(info, ref, 'T')
                    else:
                        if self.type == self.SATELLITE:
                            if self.isStream:
                                return _('Internet')
                            if self.ref:
                                return self.getSatelliteName(self.ref)
                            return self.getSatelliteName(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
                        else:
                            if self.type == self.ALLREF:
                                tmpref = self.getReferenceType(refstr, ref)
                                if 'Bouquet' in tmpref or 'Satellit' in tmpref or 'Provider' in tmpref:
                                    return ' '
                                if '%3a' in tmpref:
                                    return (':').join(refstr.split(':')[:10])
                                return tmpref
                            if self.type == self.FORMAT:
                                num = bouq = ''
                                tmp = self.sfmt[:].split('%')
                                if tmp:
                                    ret = tmp[0]
                                    tmp.remove(ret)
                                else:
                                    return ''
                                for line in tmp:
                                    f = line[:1]
                                    if f == 'N':
                                        name = ref and (info.getName(ref) or 'N/A') or info.getName() or 'N/A'
                                        postfix = ''
                                        if self.ref:
                                            postfix = ' (alter)'
                                        name += postfix
                                        ret += name.replace('\xc2\x86', '').replace('\xc2\x87', '')
                                    else:
                                        if f == 'n':
                                            try:
                                                service = self.source.serviceref
                                                num = service and service.getChannelNum() or None
                                            except:
                                                num = None

                                            if num:
                                                ret += str(num)
                                            else:
                                                num, bouq = self.getServiceNumber(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
                                                ret += num and str(num) or ''
                                        else:
                                            if f == 'B':
                                                num, bouq = self.getServiceNumber(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
                                                ret += bouq
                                            else:
                                                if f == 'P':
                                                    if self.isStream:
                                                        if self.refstr and '%3a//' in self.refstr:
                                                            ret += self.getIPTVProvider(self.refstr)
                                                        else:
                                                            ret += self.getIPTVProvider(refstr)
                                                    elif self.ref:
                                                        ret += self.getProviderName(self.ref)
                                                    elif ref:
                                                        ret += self.getProviderName(ref)
                                                    else:
                                                        ret += info.getInfoString(iServiceInformation.sProvider) or ''
                                                else:
                                                    if f == 'R':
                                                        if self.refstr:
                                                            ret += self.refstr
                                                        else:
                                                            ret += refstr
                                                    else:
                                                        if f == 'S':
                                                            if self.isStream:
                                                                ret += _('Internet')
                                                            elif self.ref:
                                                                ret += self.getSatelliteName(self.ref)
                                                            else:
                                                                ret += self.getSatelliteName(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
                                                        else:
                                                            if f == 'A':
                                                                tmpref = self.getReferenceType(refstr, ref)
                                                                if 'Bouquet' in tmpref or 'Satellit' in tmpref or 'Provider' in tmpref:
                                                                    ret += ' '
                                                                elif '%3a' in tmpref:
                                                                    ret += (':').join(refstr.split(':')[:10])
                                                                else:
                                                                    ret += tmpref
                                                            else:
                                                                if f in 'TtsFfiOMpYroclhmgbe':
                                                                    if self.ref:
                                                                        ret += self.getTransponderInfo(self.info, self.ref, f)
                                                                    else:
                                                                        ret += self.getTransponderInfo(info, ref, f)
                                    ret += line[1:]

                                return '%s' % ret.replace('N/A', '').strip()
        return

    text = property(getText)

    def neededChange(self):
        if self.what:
            Converter.changed(self, self.what)
            self.what = None
        return

    def forceChanged(self, what):
        if what == True:
            self.refstr = self.isStream = self.ref = self.info = self.tpdata = None
            Converter.changed(self, (self.CHANGED_ALL,))
            self.what = None
        return

    def changed(self, what):
        if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart,):
            self.refstr = self.isStream = self.ref = self.info = self.tpdata = None
            if self.type in (self.NUMBER, self.BOUQUET) or self.type == self.FORMAT and ('%n' in self.sfmt or '%B' in self.sfmt):
                self.what = what
                self.Timer.start(200, True)
            else:
                Converter.changed(self, what)
        return

