# The FLAIR study dataset

## Background information
**Study Title**: A Crossover Study Comparing Two Automated Insulin Delivery System
Algorithms (PID vs. PID + Fuzzy Logic) in Individuals with Type 1
Diabetes (FLAIR- Fuzzy Logic Automated Insulin Regulation)

**Description**: A randomized crossover trial will compare the efficacy and safety of an
automated insulin delivery (AID) system with a proportional-integral-
derivative (PID) algorithm versus an automatic insulin delivery (AID) system
with a PID algorithm enhanced with a Fuzzy Logic algorithm.
    
**Devices**: The Minimed 670G 4.0 Advanced Hybrid Closed-Loop (AHCL) (PID +
Fuzzy Logic) pump with the Guardian Sensor (3) continuous glucose
monitoring sensor.

## Data Description:
The study data folder is named **FLAIRPublicDataSet**
From the DataGlossary.rtf file, the following relevant files were identified which are stored in the **Data Tables** subfolder.

* **FLAIRDeviceCGM.txt**: List of CGM data downloaded
* **FLAIRDevicePump.txt**: List of pump data dowloaded 
* **PtRoster.txt**: Patient Roster

These are csv files ("|" separator) and host many columns related to the Medtronic pump events and the guardian cgm. The glossary provides information about each column. While there are many columns, the following were identified as relevant.

**FLAIRDeviceCGM**:

* **PtID**: Patient ID
* **DataDtTm**: Date-time of sensor glucose reading
* **CGM**: Sensor glucose aka CGM - mdDl or mmol/L
* **DataDtTm_adjusted**: Adjusted value of DataDtTm 

**FLAIRDevicePump**:

* **PtID**: Patient ID
* **DataDtTm**: Date-time of pump data
* **NewDeviceDtTm**: The new date and time if this was changed in the device
* **BolusType**: Bolus type - The bolus insulin delivery type [Normal, Square, Dual (normal part), or Dual (square part)]
* **BolusDeliv**: Bolus volume delivered (U) - The number of insulin units actually delivered during the bolus insulin delivery
* **ExtendBolusDuration**: Duration of the square portion of either a square bolus or a dual wave bolus
* **BasalRt**: Basal Rate (U/h) - The active basal insulin delivery rate in units per hour
* **BasalRtUnKnown**: Basal rate unknown as marked in the carelink file
* **TempBasalAmt**: Temp basal amount - If a temp basal was applied on the pump, this value is the temp basal amount
* **TempBasalType**: Temp basal type - The type of temporary basal adjustment (insulin rate or percent of basal)
* **TempBasalDur**: Temp basal duration (h:mm:ss) - The length of time for the temporary basal insulin delivery
* **Suspend**: State "Suspend" when the pump is suspended and "Resumed" when the pump is resumed 



# Analysis of the Data
The study data was analyzed to understand which data is relevant, how it must be manipulated and interpreted in order to obtain the true delivered insulin amounts. The results are mostly based on the analysis in the jupyter notebook `understand-flair-dataset.ipynb`

**Leading Questions**: 
* Do we need to track DataDtTm_adjusted or can we rely on DataDtTm?
* How often do NewDeviceDtTm** events happen and do we need to account fo these or is DataDtTm sufficient?
* How often do BasalRtUnKnown** events happen and how should we handle these?
* Are TempBasalAmt reflected in the BasalRt? Is the value a rate (U/h) or depend on the TempBasalType (Percent/Rate)?
* Do we have to keep track of temporary basal durations events (TempBasalDur) or do we get a normal basal rate at the end of the basal rate?
* How do we know if the temp basal rate is ended earlier than programmed
* How often does the pump suspend (Suspend)? Should we stop counting basal rates in this time?
* Do suspend events stop bolus deliveries? Do we need to account for it?

## General Findings
* **Temp Basal:** We have 1446 temp basal values. only 9 of these are set by insulin rate, the others are in percent. These need to be factored in.
* **Suspend:** There are 72424 suspend events. These need to be factored in.
* **Date Adjustments:** There are many adjusted datetime events for CGM (none for Insulin). We need to understand how to factor them in.
* **Date time strings**: From manual inspection we know that are date time strings without time component. We treat those without as midnight (00AM). If we don't do this in two steps, the loading is extremely slow because python needs to dynamically adjust the formatter. 

## Datetime Adjustments
<div class="alert alert-block alert-warning">
<b>Date Adjustments:</b> We need to use the adjusted datetimes for cgm, when it exists.
</div>

## Basal Rates
### Background information
According to Lane, 100% refers to the normal basal rate. Medtronic allows setting temp basal percentages from 0 (shut off) to 200% (twice the basal rate). These values are confirmed by the histogram of the data. This is confirmed by the *Medtronic Manual* [1,2]
![Basal Rate Histograms](assets/flair_basal_rate_histograms.svg)

**Temp basal rates:** "The duration of the temp basal rate can range from 30 minutes to 24 hours. After the temp basal rate delivery is completed or canceled, the programmed basal pattern resumes. The temp basal rates and preset temp basal rates can be defined using either a **percentage** of the current basal pattern or by setting a *specific rate*, as described [...]"

**Percent:** "Percent delivers a percentage of the basal rates programmed in the active basal pattern for the duration of the temp basal rate. The temp basal amount is rounded down to the next 0.025 units if the basal rate is set at less than 1 unit per hour, or to the next 0.05 units if the basal rate is set at more than 1 unit per hour. Temp basal rates can be set to deliver from *0% to 200%* of the scheduled basal rate. The *percentage used is based on the largest basal rate scheduled during the temp basal rate duration** and is **limited by the Max basal rate*."

**Rate**: "delivers a fixed basal insulin rate in *units per hour* for the duration of the temp basal rate. The amount set is *limited by the Max basal rate*"

[1] MiniMed-780G-system-user-guide-with-Guardian-4-sensor.pdf
[2] user_guide_minimed_670g_pump-skompresowany.pdf


## What we learned about basal rates

![Basal Rate Histograms](assets/flair_events_around_temporary_basal_rates.png)
>**Description**: The figure above shows that temporary basal rates are not reflected in the reported basal rates.

* We have no unknown basal rates, therefore this column can be ignored
* Standard basal rates do not reflect temporary basal rate changes
* Temporary basal rates are either given in percent [%] of the normal basal (TempBasalType=='Percent') or as a delivery rate [U/h]  replacing standard basal (TempBasalType=='Rate') 
* During temp basal rates are active, Standard BasalRt events can change and are reported

**Percent**:
* Standard Basal rates are reported shortly after temp basal start and stop
* Temporary Basal Percent rates are reported **twice**, with the same timestamp but the duration format differs with leading 0 or without leading zeros for the hour (e.g. 00:15:00) vs.(0:15:00) 
* Interpreting Temp Basal of 100 Percent:The manual notices that *The percentage used is based on the largest basal rate scheduled during the temp basal rate duration*. So a value of 100% would change the basal rate to the highest standard basal rate, even if it occurs occurs within the duration of the temp basal rate. (*Assumption*)

**Rate:**
* There are only 9 cases where temporary basal is "Rate", in these cases, standard basal rate is not reported shortly after the temp basal rate *starts*
* Temporary Basal Percent rates are reported **once**, without leading 0 for duration hour (0:15:00) 

**Takeaway:** 
To reconstruct true basal rates, we need to consider the TempBasalAmt and TempBasalType. We can use the BasalRt events as a basis and apply the TempBasalAmt for the duration of the TempBasalDur. Depending on the value of the TempBasalType, we either need to multiply the BasalRt by the TempBasalAmt (when TempBasalType is "Percent") or we can directly set the BasalRt to the TempBasalAmt (when TempBasalType is "rate"). 

To create the correct event history, we take advantage of the fact that basal rates are reported shortly after a Percent rate is set. Here, we simply multiply all basal rates within the temp basal duration period. After the temp basal duration, the standard basal rate is reported and automatically takes over. In the "Rate" case, we know that the standard basal rate is not reported shortly after the temp basal starts, so we need to treat the event as a new basal rate by copying the temp basal amount. While the temp basal Rate is set, standard basal rate changes should be ignored, we do this by setting all basal rates within the active duration to NaN (not 0!). As before, we take advantage of the fact that after the temp basal stops, a standard basal event is reported and automtaically takes over. 

 ![Absolute Basal Rates](assets/flair_absolute_basal_rates.png)

>**Description**: The figure above shows the result of applying the method described in the previous section to reconstruct the true basal rates. 

### What we learned about Pump Suspends
![Suspend Events](assets/flair_suspends.png)
* **End suspend without start:**  The very small difference is likely due to glucose suspend events that were started before the observation period. But this makes matching a little *more difficult*. We want to make sure we match the right pairs!
* **Most users start with NORMAL_PUMPING:** For the majority of users we get a NORMAL_PUMPING event as the first Suspend event without a previous Suspend event. This could be because a) the pump was being set-up (e.g. catridge change etc.) and reported normal operation (to be verified) or b) there was a suspend event before the data collection started (unlikely because suspends are often short). 
* **First Resume event**: For those users whose first suspend event is a resume to normal pumping event, we don't know how long before the pump was suspended. The average time between the first insulin event and this resume event is roughly 0.25 hours. However, the maximum time is >10 hours.
* **Not reflected in Basal**: Suspend events are not reflected in the reported basal or temporary basal rates. 
* **Basal rates** are *not* reported before/after a suspend event starts/stops

![Suspend Events with CGM](assets/flair_suspends_with_cgm.png)
